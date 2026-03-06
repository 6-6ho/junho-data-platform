"""Session persistence tests for ShoppingEventGenerator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "shop-generator"))

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from generators.shopping_event import ShoppingEventGenerator


def _make_generator():
    """Create generator without DB connection or real settings."""
    mock_settings = MagicMock()
    mock_settings.DB_HOST = "localhost"
    mock_settings.POSTGRES_DB = "app"
    mock_settings.POSTGRES_USER = "postgres"
    mock_settings.POSTGRES_PASSWORD = "postgres"

    with patch("generators.shopping_event.get_settings", return_value=mock_settings), \
         patch.object(ShoppingEventGenerator, "_load_products_from_db", return_value=[]):
        gen = ShoppingEventGenerator(chaos_mode=False)
    return gen


def test_same_user_same_session():
    """Same user within session window -> same session_id."""
    gen = _make_generator()
    sid1 = gen._get_or_create_session("user_a")
    sid2 = gen._get_or_create_session("user_a")
    assert sid1 == sid2


def test_different_users_different_sessions():
    """Different users -> different session_ids."""
    gen = _make_generator()
    sid1 = gen._get_or_create_session("user_a")
    sid2 = gen._get_or_create_session("user_b")
    assert sid1 != sid2


def test_expired_session_new_id():
    """After session expires, a new session_id is created."""
    gen = _make_generator()
    sid1 = gen._get_or_create_session("user_a")

    # Force expiration
    gen.active_sessions["user_a"]["expires_at"] = datetime.now() - timedelta(seconds=1)

    sid2 = gen._get_or_create_session("user_a")
    assert sid1 != sid2


def test_cleanup_expired_sessions():
    """_cleanup_expired_sessions removes only expired entries."""
    gen = _make_generator()

    # Create sessions
    gen._get_or_create_session("alive")
    gen._get_or_create_session("dead")

    # Expire one
    gen.active_sessions["dead"]["expires_at"] = datetime.now() - timedelta(seconds=1)

    # Force cleanup (counter must reach 1000)
    gen._event_counter = 999
    gen._cleanup_expired_sessions()

    assert "alive" in gen.active_sessions
    assert "dead" not in gen.active_sessions
