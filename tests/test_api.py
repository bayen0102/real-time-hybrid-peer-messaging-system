from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


def test_health_check():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "Messaging Management API"
    }
def test_get_messages():
    response = client.get("/messages")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    if len(data) > 0:
        message = data[0]

        assert "sender" in message
        assert "receiver" in message
        assert "message" in message
        assert "timestamp" in message

def test_messages_per_hour():
    response = client.get("/analytics/messages-per-hour")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    if len(data) > 0:
        row = data[0]

        assert "hour" in row
        assert "message_count" in row
        assert isinstance(row["message_count"], int)

def test_messages_per_hour_with_hours_filter():
    response = client.get("/analytics/messages-per-hour?hours=24")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_messages_per_hour_rejects_invalid_hours():
    response = client.get("/analytics/messages-per-hour?hours=0")
    assert response.status_code == 422