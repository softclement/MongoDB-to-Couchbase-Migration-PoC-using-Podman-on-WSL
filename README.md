# MongoDB to Couchbase Migration PoC

> **Platform:** WSL Ubuntu + Podman &nbsp;|&nbsp; **Language:** Python 3.12 &nbsp;|&nbsp; **Status:** Learning PoC

A hands-on proof of concept demonstrating a NoSQL-to-NoSQL migration from **MongoDB 8** to **Couchbase 8 Community Edition** using Python SDKs running in Podman containers on WSL.

Simulates a banking-style dataset and walks through data generation, migration with **elapsed-time tracking**, validation, and SQL++ verification end-to-end.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  WSL Ubuntu  ·  Podman (nosql-net bridge)                          │
│                                                                    │
│  ┌─────────────────┐    pymongo     ┌───────────────────────────┐  │
│  │  MongoDB 8      │ ────────────►  │  Python 3.12              │  │
│  │  port 27017     │                │                           │  │
│  │                 │                │  generate_data.py         │  │
│  │  customers      │  couchbase SDK │  mongo_to_couchbase.py    │  │
│  │  accounts       │  ◄──────────── │    ⏱ start/end/duration  │  │
│  │  transactions   │                │  validation.py            │  │
│  └─────────────────┘                └──────────┬────────────────┘  │
│                                                │ upsert            │
│                                                ▼                   │
│                                 ┌──────────────────────────────┐   │
│                                 │  Couchbase 8 CE              │   │
│                                 │  port 8091  (UI + REST)      │   │
│                                 │  port 11210 (SDK / KV)       │   │
│                                 │                              │   │
│                                 │  customer_bucket (256 MB)    │   │
│                                 │    type: customer            │   │
│                                 │    type: account             │   │
│                                 │    type: transaction         │   │
│                                 │                              │   │
│                                 │  Query Workbench (SQL++)     │   │
│                                 └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Dataset

| Collection   | Documents |
|--------------|----------:|
| customers    |    10,000 |
| accounts     |    20,000 |
| transactions |    80,000 |
| **Total**    |**110,000**|

---

## Repository Structure

```
mongodb-couchbase-migration-poc/
├── README.md
├── requirements.txt
├── generate_data.py          # seed MongoDB with Faker data
├── mongo_to_couchbase.py     # migrate + capture timing
├── validation.py             # count reconciliation
├── cleanup.sh                # stop & remove containers
├── reports/
│   └── migration_summary.txt
└── screenshots/
```

---

## Environment

| Component                   | Version  |
|-----------------------------|----------|
| WSL Ubuntu                  | 22.04+   |
| Podman                      | Latest   |
| MongoDB                     | 8.x      |
| Couchbase Community Edition | 7.6.x    |
| Python                      | 3.12     |
| pymongo                     | Latest   |
| couchbase SDK               | Latest   |
| faker                       | Latest   |

> **Note:** Credentials in this PoC (`Password123!`) are for local development only.
> Never use them in production.

---

## Prerequisites

- WSL 2 with Ubuntu 22.04 or later
- Podman installed (`sudo apt install podman`)
- Python 3.12 (`sudo apt install python3.12 python3.12-venv`)
- At least 2 GB free RAM

---

# Step 1 — Create Project Directory

```bash
mkdir -p ~/nosql-poc
cd ~/nosql-poc
```

---

# Step 2 — Create Podman Network

```bash
podman network create nosql-net
```

Verify:

```bash
podman network ls
```

Expected:

```
NETWORK ID    NAME        DRIVER
xxxxxxxxxxxx  nosql-net   bridge
```

---

# Step 3 — Start MongoDB Container

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

# Step 4 — Start Couchbase Container

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

# Step 5 — Configure Couchbase

Open the Couchbase Web UI:

```
http://localhost:8091
```

Select **Setup New Cluster** and use these settings:

```
Cluster Name : couchbase-poc
Username     : Administrator
Password     : Password123!
```

**Create Bucket:**

```
Bucket Name : customer_bucket
RAM Quota   : 256 MB
```

**Create Primary Index** — open the Query Workbench at:

```
http://localhost:8091/ui/index.html#/query/workbench
```

Execute:

```sql
CREATE PRIMARY INDEX idx_customer ON customer_bucket;
```

---

# Step 6 — Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install pymongo couchbase faker
```

Or from the requirements file:

```bash
pip install -r requirements.txt
```

---

# Step 7 — Generate Sample Data

```bash
python generate_data.py
```

Expected output:

```
==================================================
  Data Generation — MongoDB
==================================================
  Generating 10,000 customers...
  Generating 20,000 accounts...
  Generating 80,000 transactions (batch size 10,000)...

Data Generation Complete
--------------------------------------------------
  Customers    :   10,000
  Accounts     :   20,000
  Transactions :   80,000
  Total        :  110,000
==================================================
```

**Verify in MongoDB:**

```bash
podman exec -it mongodb mongosh
```

```javascript
use demo
db.customers.countDocuments()      // 10000
db.accounts.countDocuments()       // 20000
db.transactions.countDocuments()   // 80000
exit
```

---

# Step 8 — Run Migration

```bash
python mongo_to_couchbase.py
```

The script records **start time**, **end time**, and **duration** per collection and for the overall run.

Expected output:

```
============================================================
  MongoDB → Couchbase Migration
============================================================

  Overall Start : 2025-06-01 10:00:00 UTC

  [Customers]   Starting   : 2025-06-01 10:00:01 UTC
  [Customers]   Completed  : 2025-06-01 10:00:12 UTC
  [Customers]   Duration   : 11.34s
  [Customers]   Migrated   : 10,000 / 10,000  (errors: 0)

  [Accounts]    Starting   : 2025-06-01 10:00:13 UTC
  [Accounts]    Completed  : 2025-06-01 10:00:38 UTC
  [Accounts]    Duration   : 25.17s
  [Accounts]    Migrated   : 20,000 / 20,000  (errors: 0)

  [Transactions] Starting  : 2025-06-01 10:00:39 UTC
  [Transactions] Completed : 2025-06-01 10:02:24 UTC
  [Transactions] Duration  : 1m 45s
  [Transactions] Migrated  : 80,000 / 80,000  (errors: 0)

============================================================
  Migration Summary
============================================================
  Collection           Docs     Start                    End                      Duration
  -------------------- -------- ------------------------ ------------------------ ----------
  Customers          10,000     2025-06-01 10:00:01 UTC  2025-06-01 10:00:12 UTC      11.34s
  Accounts           20,000     2025-06-01 10:00:13 UTC  2025-06-01 10:00:38 UTC      25.17s
  Transactions       80,000     2025-06-01 10:00:39 UTC  2025-06-01 10:02:24 UTC      1m 45s
  -------------------- --------
  TOTAL             110,000

  Overall Start    : 2025-06-01 10:00:00 UTC
  Overall End      : 2025-06-01 10:02:25 UTC
  Overall Duration : 2m 25s
  Total Errors     : 0

  Status           : SUCCESS ✓
============================================================
```

Save the report:

```bash
mkdir -p reports
python mongo_to_couchbase.py | tee reports/migration_summary.txt
```

---

# Step 9 — Validate Migration

```bash
python validation.py
```

Expected output:

```
=============================================
  MongoDB → Couchbase Validation
=============================================

  Collection      MongoDB   Couchbase   Match
  --------------- --------- ----------- ------
  customer         10,000      10,000       ✓
  account          20,000      20,000       ✓
  transaction      80,000      80,000       ✓
  --------------- ---------  ----------
  TOTAL           110,000     110,000

  VALIDATION PASSED ✓
=============================================
```

---

# Step 10 — Verify Data in Couchbase

## Option 1 — Query Workbench (SQL++)

```sql
SELECT COUNT(*) cnt FROM customer_bucket WHERE type = 'customer';
SELECT COUNT(*) cnt FROM customer_bucket WHERE type = 'account';
SELECT COUNT(*) cnt FROM customer_bucket WHERE type = 'transaction';
```

Expected:

```
customer      10,000
account       20,000
transaction   80,000
```

## Option 2 — Sample Documents

```sql
SELECT * FROM customer_bucket WHERE type = 'customer'    LIMIT 5;
SELECT * FROM customer_bucket WHERE type = 'account'     LIMIT 5;
SELECT * FROM customer_bucket WHERE type = 'transaction' LIMIT 5;
```

## Option 3 — Group by Type (WSL CLI)

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
    { "type": "customer",    "cnt": 10000 },
    { "type": "account",     "cnt": 20000 },
    { "type": "transaction", "cnt": 80000 }
  ]
}
```

---

# Migration Validation Summary

| Document Type | MongoDB | Couchbase | Status |
|---------------|--------:|----------:|--------|
| customer      |  10,000 |    10,000 | ✓      |
| account       |  20,000 |    20,000 | ✓      |
| transaction   |  80,000 |    80,000 | ✓      |
| **Total**     |**110,000**|**110,000**| **PASSED** |

---

# Results

```
Source Database  : MongoDB 8
Target Database  : Couchbase 8 Community Edition
Collections      : 3
Customers        : 10,000
Accounts         : 20,000
Transactions     : 80,000
Total Documents  : 110,000
Migration Status : SUCCESS
Validation       : PASSED
Timing           : Per-collection start / end / duration captured
Platform         : WSL + Podman
Automation       : Python 3.12
```

---

# Cleanup

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

## Learning Outcomes

- MongoDB administration and collection design
- Couchbase cluster setup, bucket management, and primary index creation
- Podman container networking on WSL
- Python-based NoSQL migration with batch upsert
- Migration effort tracking — start time, end time, duration per collection
- Data validation and count reconciliation
- Couchbase SQL++ querying (`WHERE type = '...'`)
- End-to-end NoSQL modernisation workflow
