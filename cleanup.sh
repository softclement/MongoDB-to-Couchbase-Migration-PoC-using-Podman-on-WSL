#!/bin/bash
# cleanup.sh — stop and remove all PoC containers and the Podman network.

echo "Stopping containers..."
podman stop mongodb couchbase 2>/dev/null || true

echo "Removing containers..."
podman rm mongodb couchbase 2>/dev/null || true

echo "Removing network..."
podman network rm nosql-net 2>/dev/null || true

echo "Cleanup complete."
