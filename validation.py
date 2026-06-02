"""
validation.py
Compares document counts between MongoDB (source) and Couchbase (target).
Exits with code 0 on PASS, code 1 on FAIL.
"""

import sys
import time

from pymongo import MongoClient
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from couchbase.exceptions import CouchbaseException

# ── Connection settings ────────────────────────────────────────────────────────
MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "demo"

CB_HOST    = "couchbase://localhost"
CB_USER    = "Administrator"
CB_PASS    = "Password123!"
CB_BUCKET  = "customer_bucket"

# Retry N1QL queries a few times in case the index is still building
N1QL_RETRIES = 3
N1QL_RETRY_DELAY = 3   # seconds


def cb_count(cluster, bucket: str, doc_type: str) -> int:
    """Run a SQL++ COUNT query with retry logic."""
    query = f"SELECT RAW COUNT(*) FROM `{bucket}` WHERE type = '{doc_type}'"
    for attempt in range(1, N1QL_RETRIES + 1):
        try:
            result = cluster.query(query)
            rows   = list(result)
            return rows[0] if rows else 0
        except CouchbaseException as exc:
            if attempt < N1QL_RETRIES:
                print(f"    [RETRY {attempt}] N1QL error ({exc}). Retrying in {N1QL_RETRY_DELAY}s...")
                time.sleep(N1QL_RETRY_DELAY)
            else:
                raise


def main():
    print()
    print("=" * 45)
    print("  MongoDB → Couchbase Validation")
    print("=" * 45)

    # ── MongoDB counts ──────────────────────────────────────────────
    print("\n  Connecting to MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    db           = mongo_client[MONGO_DB]

    mongo_counts = {
        "customer":    db.customers.count_documents({}),
        "account":     db.accounts.count_documents({}),
        "transaction": db.transactions.count_documents({}),
    }
    mongo_client.close()
    print("  MongoDB counts retrieved.")

    # ── Couchbase counts ────────────────────────────────────────────
    print("\n  Connecting to Couchbase...")
    auth    = PasswordAuthenticator(CB_USER, CB_PASS)
    cluster = Cluster(CB_HOST, ClusterOptions(auth))
    cluster.wait_until_ready(timeout=15)

    cb_counts = {
        "customer":    cb_count(cluster, CB_BUCKET, "customer"),
        "account":     cb_count(cluster, CB_BUCKET, "account"),
        "transaction": cb_count(cluster, CB_BUCKET, "transaction"),
    }
    print("  Couchbase counts retrieved.")

    # ── Compare ─────────────────────────────────────────────────────
    print()
    print("-" * 45)
    print(f"  {'Collection':<15} {'MongoDB':>10} {'Couchbase':>12} {'Match':>6}")
    print(f"  {'-'*15} {'-'*10} {'-'*12} {'-'*6}")

    all_pass = True
    for doc_type in ("customer", "account", "transaction"):
        m_cnt = mongo_counts[doc_type]
        c_cnt = cb_counts[doc_type]
        match = "✓" if m_cnt == c_cnt else "✗"
        if m_cnt != c_cnt:
            all_pass = False
        print(f"  {doc_type:<15} {m_cnt:>10,} {c_cnt:>12,} {match:>6}")

    mongo_total = sum(mongo_counts.values())
    cb_total    = sum(cb_counts.values())
    print(f"  {'-'*15} {'-'*10} {'-'*12}")
    print(f"  {'TOTAL':<15} {mongo_total:>10,} {cb_total:>12,}")
    print()

    if all_pass:
        print("  VALIDATION PASSED ✓")
        print("=" * 45)
        sys.exit(0)
    else:
        print("  VALIDATION FAILED ✗")
        print("  One or more counts do not match.")
        print("=" * 45)
        sys.exit(1)


if __name__ == "__main__":
    main()
