"""Seed 100K synthetic messages for benchmarking.

Synthetic rows use sender/receiver names like 'bench_user_7' and timestamps
spread over the last 30 days. Remove them with: python scripts/seed_messages.py --clean
"""
import os
import sys

import psycopg

N_ROWS = 100_000


def connect():
    # Defaults match compose.yaml as seen from the host machine (port 5434).
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5434"),
        dbname=os.getenv("DB_NAME", "messaging_db"),
        user=os.getenv("DB_USER", "bay"),
        password=os.getenv("DB_PASSWORD", "bayproject"),
        autocommit=True,
    )


def main():
    with connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM messages WHERE sender LIKE 'bench_user_%'")
        if "--clean" in sys.argv:
            print("Removed synthetic benchmark messages.")
            return

        cur.execute("SELECT setseed(0.42)")  # reproducible timestamps
        cur.execute(
            f"""
            INSERT INTO messages (sender, receiver, message, timestamp)
            SELECT 'bench_user_' || mod(i, 100),
                   'bench_user_' || mod(i + 1, 100),
                   'bench-message-' || i,
                   NOW() - random() * INTERVAL '30 days'
            FROM generate_series(1, {N_ROWS}) AS i
            """
        )
        cur.execute("ANALYZE messages")
        print(f"Seeded {N_ROWS} synthetic messages over the last 30 days.")


if __name__ == "__main__":
    main()