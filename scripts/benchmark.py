"""Benchmark hourly aggregation with and without the timestamp index.

Measures (median of RUNS runs after WARMUP warm-up runs):
  1. The SQL query used by get_messages_per_hour(hours=24)
  2. GET /analytics/messages-per-hour?hours=24 over HTTP
  3. GET /analytics/messages-per-hour (no filter) over HTTP

The index is dropped, measured, recreated, measured again, and always left
recreated at the end so the database matches database/schema.sql.
"""
import os
import statistics
import time
import urllib.request

import psycopg

INDEX_NAME = "idx_messages_timestamp"
HOURS = 24
RUNS = 200
WARMUP = 20
API_URL = os.getenv("API_URL", "http://localhost:8000")
ENDPOINT = f"{API_URL}/analytics/messages-per-hour"

# Same SQL as the `hours` branch of get_messages_per_hour() in database.py.
QUERY = """
    SELECT
        DATE_TRUNC('hour', timestamp) AS hour,
        COUNT(*) AS message_count
    FROM messages
    WHERE timestamp >= NOW() - make_interval(hours => %s::int)
    GROUP BY hour
    ORDER BY hour
"""


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5434"),
        dbname=os.getenv("DB_NAME", "messaging_db"),
        user=os.getenv("DB_USER", "bay"),
        password=os.getenv("DB_PASSWORD", "bayproject"),
        autocommit=True,
    )


def median_ms(fn):
    for _ in range(WARMUP):
        fn()
    samples = []
    for _ in range(RUNS):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def run_query(cur):
    cur.execute(QUERY, (HOURS,))
    cur.fetchall()


def call_api(suffix):
    with urllib.request.urlopen(f"{ENDPOINT}{suffix}") as resp:
        resp.read()


def uses_index(cur):
    plan_sql = "EXPLAIN " + QUERY.replace("%s::int", str(HOURS))
    cur.execute(plan_sql)
    return any("Index" in row[0] for row in cur.fetchall())


def measure(cur):
    return {
        "query": median_ms(lambda: run_query(cur)),
        "endpoint_24h": median_ms(lambda: call_api(f"?hours={HOURS}")),
        "endpoint_all": median_ms(lambda: call_api("")),
        "uses_index": uses_index(cur),
    }


def main():
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM messages")
        total_rows = cur.fetchone()[0]

        try:
            cur.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
            cur.execute("ANALYZE messages")
            without = measure(cur)

            cur.execute(f"CREATE INDEX {INDEX_NAME} ON messages(timestamp)")
            cur.execute("ANALYZE messages")
            with_idx = measure(cur)
        finally:
            cur.execute(f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON messages(timestamp)")

    print(f"\nRows in messages: {total_rows}")
    print(f"Median of {RUNS} runs (after {WARMUP} warm-up runs), hours={HOURS}")
    print(f"Planner used an index without/with index: "
          f"{without['uses_index']} / {with_idx['uses_index']}\n")
    print("| Measurement | Without index | With index |")
    print("|---|---|---|")
    print(f"| Time-range aggregation query (SQL, last {HOURS} h) "
          f"| {without['query']:.1f} ms | {with_idx['query']:.1f} ms |")
    print(f"| `GET /analytics/messages-per-hour?hours={HOURS}` "
          f"| {without['endpoint_24h']:.1f} ms | {with_idx['endpoint_24h']:.1f} ms |")
    print(f"| `GET /analytics/messages-per-hour` (no filter, full table) "
          f"| {without['endpoint_all']:.1f} ms | {with_idx['endpoint_all']:.1f} ms |")


if __name__ == "__main__":
    main()