from fastapi import FastAPI
from database import (
    get_clients,
    get_messages,
    get_messages_by_user,
    get_messages_per_hour
)
from redis_client import get_user_status

app = FastAPI(
    title="Messaging Management API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Messaging Management API"
    }


@app.get("/users")
def users():
    return get_clients()
@app.get("/messages")
def messages():
    return get_messages()

@app.get("/messages/{user_id}")
def messages_by_user(user_id: str):
    return get_messages_by_user(user_id)

@app.get("/analytics/messages-per-hour")
def messages_per_hour():
    return get_messages_per_hour()

@app.get("/presence/{user_id}")
def user_presence(user_id: str):
    return {
        "user": user_id,
        "status": get_user_status(user_id)
    }