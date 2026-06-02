"""
generate_data.py
Generates synthetic banking data and inserts it into MongoDB.
Collections: customers (10,000), accounts (20,000), transactions (80,000)
"""

import random
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

MONGO_URI  = "mongodb://localhost:27017"
DB_NAME    = "demo"

CUSTOMER_COUNT    = 10_000
ACCOUNT_COUNT     = 20_000
TRANSACTION_COUNT = 80_000

ACCOUNT_TYPES  = ["checking", "savings", "credit", "loan"]
TRANS_TYPES    = ["debit", "credit", "transfer", "payment", "refund"]
TRANS_STATUSES = ["completed", "pending", "failed"]


def generate_customers(n: int) -> list[dict]:
    print(f"  Generating {n:,} customers...")
    customers = []
    for i in range(1, n + 1):
        customers.append({
            "_id":        f"CUST{i:06d}",
            "first_name": fake.first_name(),
            "last_name":  fake.last_name(),
            "email":      fake.unique.email(),
            "phone":      fake.phone_number(),
            "address": {
                "street": fake.street_address(),
                "city":   fake.city(),
                "state":  fake.state_abbr(),
                "zip":    fake.zipcode(),
            },
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            "created_at":    fake.date_time_between(start_date="-5y").isoformat(),
        })
    return customers


def generate_accounts(n: int, customer_ids: list[str]) -> list[dict]:
    print(f"  Generating {n:,} accounts...")
    accounts = []
    for i in range(1, n + 1):
        accounts.append({
            "_id":         f"ACC{i:07d}",
            "customer_id": random.choice(customer_ids),
            "type":        random.choice(ACCOUNT_TYPES),
            "balance":     round(random.uniform(0, 50_000), 2),
            "currency":    "USD",
            "status":      random.choice(["active", "active", "active", "inactive"]),
            "opened_at":   fake.date_time_between(start_date="-4y").isoformat(),
        })
    return accounts


def generate_transactions(n: int, account_ids: list[str]) -> list[dict]:
    print(f"  Generating {n:,} transactions...")
    transactions = []
    base_date = datetime.now()
    for i in range(1, n + 1):
        amount = round(random.uniform(1, 5_000), 2)
        txn_date = base_date - timedelta(days=random.randint(0, 730))
        transactions.append({
            "_id":            f"TXN{i:08d}",
            "account_id":     random.choice(account_ids),
            "type":           random.choice(TRANS_TYPES),
            "amount":         amount,
            "currency":       "USD",
            "status":         random.choice(TRANS_STATUSES),
            "merchant":       fake.company(),
            "description":    fake.sentence(nb_words=6),
            "transaction_at": txn_date.isoformat(),
        })
    return transactions


def main():
    print("=" * 50)
    print("  Data Generation — MongoDB")
    print("=" * 50)

    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]

    # Drop existing collections for a clean run
    for col in ("customers", "accounts", "transactions"):
        db[col].drop()

    # Customers
    customers = generate_customers(CUSTOMER_COUNT)
    db.customers.insert_many(customers, ordered=False)
    db.customers.create_index([("email", ASCENDING)], unique=True)

    customer_ids = [c["_id"] for c in customers]

    # Accounts
    accounts = generate_accounts(ACCOUNT_COUNT, customer_ids)
    db.accounts.insert_many(accounts, ordered=False)
    db.accounts.create_index([("customer_id", ASCENDING)])

    account_ids = [a["_id"] for a in accounts]

    # Transactions (inserted in batches to stay memory-friendly)
    BATCH = 10_000
    print(f"  Generating {TRANSACTION_COUNT:,} transactions (batch size {BATCH:,})...")
    for start in range(0, TRANSACTION_COUNT, BATCH):
        batch = generate_transactions(
            min(BATCH, TRANSACTION_COUNT - start), account_ids
        )
        # Fix IDs to be globally unique across batches
        offset = start
        for j, doc in enumerate(batch):
            doc["_id"] = f"TXN{offset + j + 1:08d}"
        db.transactions.insert_many(batch, ordered=False)
    db.transactions.create_index([("account_id", ASCENDING)])
    db.transactions.create_index([("transaction_at", ASCENDING)])

    print()
    print("Data Generation Complete")
    print("-" * 50)
    print(f"  Customers    : {db.customers.count_documents({}):>8,}")
    print(f"  Accounts     : {db.accounts.count_documents({}):>8,}")
    print(f"  Transactions : {db.transactions.count_documents({}):>8,}")
    total = (db.customers.count_documents({}) +
             db.accounts.count_documents({}) +
             db.transactions.count_documents({}))
    print(f"  Total        : {total:>8,}")
    print("=" * 50)

    client.close()


if __name__ == "__main__":
    main()
