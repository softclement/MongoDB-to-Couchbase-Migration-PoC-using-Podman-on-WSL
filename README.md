# MongoDB to Couchbase Migration PoC using Podman on WSL

## Overview

This Proof of Concept (PoC) demonstrates a NoSQL-to-NoSQL migration from MongoDB 8 to Couchbase 8 Community Edition using Python SDKs running on Podman containers in WSL.

The PoC simulates a banking-style dataset consisting of customers, accounts, and transactions and demonstrates:

* MongoDB data generation
* Multi-collection migration
* Data validation
* Reconciliation checks
* Couchbase SQL++ verification
* Environment cleanup

## Architecture

```text
MongoDB (Source)
   |
   |  customers
   |  accounts
   |  transactions
   |
Python Migration Script
   |
   v
Couchbase (Target)
   |
   |  customer documents
   |  account documents
   |  transaction documents
```
<img width="1105" height="839" alt="image" src="https://github.com/user-attachments/assets/9b849395-2b29-4c5a-9e04-e1b9a2672065" />


## Environment

| Component                   | Version |
| --------------------------- | ------- |
| WSL Ubuntu                  | Latest  |
| Podman                      | Latest  |
| MongoDB                     | 8.x     |
| Couchbase Community Edition | 8.x     |
| Python                      | 3.12    |
| pymongo                     | Latest  |
| couchbase SDK               | Latest  |
| faker                       | Latest  |

---

# Step 1 - Create Project Directory

```bash
mkdir -p ~/nosql-poc

cd ~/nosql-poc
```

---

# Step 2 - Create Podman Network

```bash
podman network create nosql-net
```

Verify:

```bash
podman network ls
```

Expected:

```text
NETWORK ID    NAME        DRIVER
xxxxxxxxxxxx  nosql-net   bridge
```

---

# Step 3 - Start MongoDB Container

```bash
podman run -d \
  --name mongodb \
  --network nosql-net \
  -p 27017:27017 \
  docker.io/library/mongo:8
```

Verify:

```bash
podman ps
```

---

# Step 4 - Start Couchbase Container

```bash
podman run -d \
  --name couchbase \
  --network nosql-net \
  -p 8091-8096:8091-8096 \
  -p 11210:11210 \
  docker.io/couchbase:community
```

Verify:

```bash
podman ps
```

---

# Step 5 - Configure Couchbase

Open:

```text
http://localhost:8091
```

Select:

```text
Setup New Cluster
```

Configuration:

```text
Cluster Name : couchbase-poc

Username     : Administrator

Password     : Password123!
```

Create Bucket:

```text
Bucket Name : customer_bucket

RAM Quota   : 256 MB
```

Create Primary Index:

Open Query Workbench:

```text
http://localhost:8091/ui/index.html#/query/workbench
```

Execute:

```sql
CREATE PRIMARY INDEX idx_customer
ON customer_bucket;
```

---

# Step 6 - Create Python Virtual Environment

```bash
python3 -m venv venv

source venv/bin/activate
```

Install packages:

```bash
pip install pymongo

pip install couchbase

pip install faker
```

---

# requirements.txt

```text
pymongo
couchbase
faker
```

---

# Step 7 - Generate Sample Data

## Collections

| Collection   | Records |
| ------------ | ------- |
| customers    | 10,000  |
| accounts     | 20,000  |
| transactions | 100,000 |

Total Documents:

```text
130,000
```

Create:

```text
generate_data.py
```

Run:

```bash
python generate_data.py
```

Expected Output:

```text
Data Generation Complete
```

---

# Verify MongoDB Data

Connect:

```bash
podman exec -it mongodb mongosh
```

Execute:

```javascript
use demo

db.customers.countDocuments()

db.accounts.countDocuments()

db.transactions.countDocuments()
```

Expected:

```text
10000

20000

100000
```

Exit:

```javascript
exit
```

---

# Step 8 - Migration Script

Create:

```text
mongo_to_couchbase.py
```

Run:

```bash
python mongo_to_couchbase.py
```

Expected Output:

```text
Starting migration...

Migration Summary
-------------------------
Customers Migrated    : 10000

Accounts Migrated     : 20000

Transactions Migrated : 100000

Total Documents       : 130000
```

Optional:

Save migration report:

```bash
mkdir -p reports

python mongo_to_couchbase.py | tee reports/migration_summary.txt
```

---

# Step 9 - Validation Script

Create:

```text
validation.py
```

Run:

```bash
python validation.py
```

Expected Output:

```text
===================================
MongoDB -> Couchbase Validation
===================================

Mongo Customers     : 10000
Couchbase Customers : 10000

Mongo Accounts      : 20000
Couchbase Accounts  : 20000

Mongo Transactions      : 100000
Couchbase Transactions  : 100000

VALIDATION PASSED
```

---

# Step 10 - Verify Data in Couchbase

## Option 1 - Couchbase Query Workbench

Open:

```text
http://localhost:8091/ui/index.html#/query/workbench
```

Execute:

```sql
SELECT COUNT(*) cnt
FROM customer_bucket
WHERE type='customer';
```

```sql
SELECT COUNT(*) cnt
FROM customer_bucket
WHERE type='account';
```

```sql
SELECT COUNT(*) cnt
FROM customer_bucket
WHERE type='transaction';
```

Expected:

```text
customer     10000

account      20000

transaction 100000
```

---

## Option 2 - View Sample Documents

```sql
SELECT *
FROM customer_bucket
WHERE type='customer'
LIMIT 5;
```

```sql
SELECT *
FROM customer_bucket
WHERE type='account'
LIMIT 5;
```

```sql
SELECT *
FROM customer_bucket
WHERE type='transaction'
LIMIT 5;
```

---

## Option 3 - Verify Multiple Counts from WSL CLI

Run:

```bash
podman exec couchbase \
/opt/couchbase/bin/cbq \
-u Administrator \
-p Password123! \
-s "SELECT type, COUNT(*) cnt FROM customer_bucket GROUP BY type;"
```

Expected:

```json
{
  "results": [
    {
      "type": "account",
      "cnt": 20000
    },
    {
      "type": "customer",
      "cnt": 10000
    },
    {
      "type": "transaction",
      "cnt": 100000
    }
  ]
}
```

---

# Migration Validation Summary

| Document Type | MongoDB | Couchbase |
| ------------- | ------- | --------- |
| customer      | 10000   | 10000     |
| account       | 20000   | 20000     |
| transaction   | 100000  | 100000    |

Validation Status:

```text
PASSED
```

---

# Repository Structure

```text
mongodb-couchbase-migration-poc/

├── README.md
├── requirements.txt
├── generate_data.py
├── mongo_to_couchbase.py
├── validation.py
├── cleanup.sh
├── reports/
│   └── migration_summary.txt
└── screenshots/
```

---

# Cleanup

Create:

```text
cleanup.sh
```

Contents:

```bash
#!/bin/bash

podman stop mongodb couchbase

podman rm mongodb couchbase

podman network rm nosql-net
```

Run:

```bash
chmod +x cleanup.sh

./cleanup.sh
```

Remove project directory:

```bash
cd ~

rm -rf ~/nosql-poc
```

---

# Results

```text
Source Database  : MongoDB 8

Target Database  : Couchbase 8

Collections      : 3

customers        : 10,000

accounts         : 20,000

transactions     : 100,000

Total Documents  : 130,000

Migration Status : SUCCESS

Validation       : PASSED

Platform         : WSL + Podman

Automation       : Python
```

## Learning Outcomes

* MongoDB administration basics
* Couchbase cluster setup
* Podman container management
* Python-based NoSQL migration
* Data validation and reconciliation
* Couchbase SQL++ querying
* End-to-end NoSQL modernization workflow
