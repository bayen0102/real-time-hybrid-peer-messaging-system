from redis_client import (
    set_user_online,
    set_user_offline,
    get_user_status
)


def test_user_presence():
    user_id = "pytest_user"

    set_user_online(user_id)
    assert get_user_status(user_id) == "online"

    set_user_offline(user_id)
    assert get_user_status(user_id) == "offline"