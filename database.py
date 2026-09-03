import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "messaging_db"),
        user=os.getenv("DB_USER", "bay"),
        password=os.getenv("DB_PASSWORD")
    )

def register_client(client_id, ip, port):
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO clients (client_id, ip, port)
                VALUES (%s, %s, %s)
                ON CONFLICT (client_id)
                DO UPDATE SET
                    ip = EXCLUDED.ip,
                    port = EXCLUDED.port
            """, (client_id, ip, int(port)))

        db.commit()

    finally:
        db.close()


def save_message(sender, receiver, message):
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages (sender, receiver, message)
                VALUES (%s, %s, %s)
            """, (sender, receiver, message))

        db.commit()

    finally:
        db.close()
def get_clients():
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT client_id, ip, port
                FROM clients
                ORDER BY client_id
            """)

            rows = cursor.fetchall()

            return [
                {
                    "client_id": row[0],
                    "ip": row[1],
                    "port": row[2]
                }
                for row in rows
            ]

    finally:
        db.close()
def get_messages():
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, sender, receiver, message, timestamp
                FROM messages
                ORDER BY timestamp
            """)

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "sender": row[1],
                    "receiver": row[2],
                    "message": row[3],
                    "timestamp": row[4]
                }
                for row in rows
            ]

    finally:
        db.close()
def get_messages_by_user(user_id):
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, sender, receiver, message, timestamp
                FROM messages
                WHERE sender = %s OR receiver = %s
                ORDER BY timestamp
            """, (user_id, user_id))

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "sender": row[1],
                    "receiver": row[2],
                    "message": row[3],
                    "timestamp": row[4]
                }
                for row in rows
            ]

    finally:
        db.close()

def get_messages_per_hour():
    db = connect_db()

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DATE_TRUNC('hour', timestamp) AS hour,
                    COUNT(*) AS message_count
                FROM messages
                GROUP BY hour
                ORDER BY hour
            """)

            rows = cursor.fetchall()

            return [
                {
                    "hour": row[0],
                    "message_count": row[1]
                }
                for row in rows
            ]

    finally:
        db.close()