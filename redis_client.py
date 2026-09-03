import os
import redis

from dotenv import load_dotenv

load_dotenv()


redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


def set_user_online(user_id):
    redis_client.set(
        f"user:{user_id}:status",
        "online"
    )


def set_user_offline(user_id):
    redis_client.set(
        f"user:{user_id}:status",
        "offline"
    )


def get_user_status(user_id):
    status = redis_client.get(
        f"user:{user_id}:status"
    )

    return status or "offline"