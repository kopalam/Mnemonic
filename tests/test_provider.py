"""Test suite for Mnemonic MemoryProvider adapter."""

import pytest

from mnemonic.provider import MnemonicProvider


@pytest.fixture
def provider():
    return MnemonicProvider(
        base_url="http://localhost:8000",
        client_id="test_client",
        user_id="test_user",
        agent_id="test_agent",
        session_id="test_session",
    )


def test_namespace_header(provider: MnemonicProvider):
    """Namespace header should be correctly formatted."""
    assert provider._headers["X-Namespace"] == "test_client:test_user:test_agent:test_session"


def test_namespace_without_session():
    """Namespace without session_id should omit the 4th segment."""
    p = MnemonicProvider(
        client_id="c", user_id="u", agent_id="a",
    )
    assert p._headers["X-Namespace"] == "c:u:a"


def test_api_key_header():
    """API key should be set as Bearer token."""
    p = MnemonicProvider(api_key="sk-test-123")
    assert p._headers["Authorization"] == "Bearer sk-test-123"
