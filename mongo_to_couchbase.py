"""
mongo_to_couchbase.py
Migrates documents from MongoDB → Couchbase Community Edition.
Tracks start time, end time, and duration per collection and overall.
"""

import time
from datetime import datetime, timezone, timedelta

from pymongo import MongoClient
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from couchbase.exceptions import CouchbaseException

# ── Connection settings ────────────────────────────────────────────────────────
MONGO_URI   = "mongodb://localhost:27017"
MONGO_DB    = "demo"

CB_HOST     = "couchbase://localhost"
CB_USER     = "Administrator"
CB_PASS     = "Password123!"
CB_BUCKET   = "customer_bucket"

# ── Tuning ─────────────────────────────────────────────────────────────────────
BATCH_SIZE  = 500          # documents upserted per iteration


# ── Helpers ────────────────────────────────────────────────────────────────────
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def migrate_collection(
    mongo_col,
    cb_collection,
    type_tag: str,
    label: str,
) -> dict:
    """
    Migrate all documents from a MongoDB collection to a Couchbase collection.
    Returns a timing + count summary dict.
    """
    start_dt  = now_utc()
    start_ts  = time.perf_counter()
    print(f"\n  [{label}] Starting   : {fmt_dt(start_dt)}")

    total     = mongo_col.count_documents({})
    migrated  = 0
    errors    = 0

    cursor = mongo_col.find({}, batch_size=BATCH_SIZE)

    for doc in cursor:
        doc_id  = str(doc.pop("_id"))
        doc["type"] = type_tag          # tag for SQL++ filtering

        try:
            cb_collection.upsert(doc_id, doc)
            migrated += 1
        except CouchbaseException as exc:
            errors += 1
            if errors <= 5:            # log first few errors only
                print(f"    [WARN] upsert failed for {doc_id}: {exc}")

    end_dt   = now_utc()
    end_ts   = time.perf_counter()
    duration = end_ts - start_ts

    print(f"  [{label}] Completed  : {fmt_dt(end_dt)}")
    print(f"  [{label}] Duration   : {fmt_duration(duration)}")
    print(f"  [{label}] Migrated   : {migrated:,} / {total:,}  (errors: {errors})")

    return {
        "label":    label,
        "total":    total,
        "migrated": migrated,
        "errors":   errors,
        "start":    fmt_dt(start_dt),
        "end":      fmt_dt(end_dt),
        "duration": fmt_duration(duration),
        "seconds":  duration,
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 60)
    print("  MongoDB → Couchbase Migration")
    print("=" * 60)

    overall_start_dt = now_utc()
    overall_start_ts = time.perf_counter()
    print(f"\n  Overall Start : {fmt_dt(overall_start_dt)}")

    # ── Connect MongoDB ────────────────────────────────────────────
    print("\n  Connecting to MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    db           = mongo_client[MONGO_DB]
    print("  MongoDB connection OK")

    # ── Connect Couchbase ──────────────────────────────────────────
    print("\n  Connecting to Couchbase...")
    auth    = PasswordAuthenticator(CB_USER, CB_PASS)
    cluster = Cluster(CB_HOST, ClusterOptions(auth))
    cluster.wait_until_ready(timeout=timedelta(seconds=15))
    bucket  = cluster.bucket(CB_BUCKET)
    scope   = bucket.default_scope()
    col     = scope.collection("_default")
    print("  Couchbase connection OK")

    # ── Migrate ────────────────────────────────────────────────────
    print("\n  Starting migration...\n" + "-" * 60)

    results = []
    results.append(migrate_collection(db.customers,    col, "customer",    "Customers"))
    results.append(migrate_collection(db.accounts,     col, "account",     "Accounts"))
    results.append(migrate_collection(db.transactions, col, "transaction", "Transactions"))

    # ── Overall totals ─────────────────────────────────────────────
    overall_end_dt = now_utc()
    overall_end_ts = time.perf_counter()
    overall_dur    = overall_end_ts - overall_start_ts

    total_docs     = sum(r["total"]    for r in results)
    total_migrated = sum(r["migrated"] for r in results)
    total_errors   = sum(r["errors"]   for r in results)

    # ── Report ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  Migration Summary")
    print("=" * 60)
    print(f"  {'Collection':<20} {'Docs':>8}  {'Start':<24} {'End':<24} {'Duration':>10}")
    print(f"  {'-'*20} {'-'*8}  {'-'*24} {'-'*24} {'-'*10}")
    for r in results:
        print(f"  {r['label']:<20} {r['migrated']:>8,}  {r['start']:<24} {r['end']:<24} {r['duration']:>10}")
    print(f"  {'-'*20} {'-'*8}")
    print(f"  {'TOTAL':<20} {total_migrated:>8,}")
    print()
    print(f"  Overall Start    : {fmt_dt(overall_start_dt)}")
    print(f"  Overall End      : {fmt_dt(overall_end_dt)}")
    print(f"  Overall Duration : {fmt_duration(overall_dur)}")
    print(f"  Total Errors     : {total_errors}")
    print()
    if total_errors == 0:
        print("  Status           : SUCCESS ✓")
    else:
        print(f"  Status           : COMPLETED WITH {total_errors} ERROR(S)")
    print("=" * 60)

    mongo_client.close()


if __name__ == "__main__":
    main()
