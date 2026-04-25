from uuid import uuid4

import pytest

from src.models.connector import Connector
from src.routes.triggers import _callback_url, _resolve_connector, _slack_workspace_id, receive_webhook


class _Request:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url


class _JsonRequest:
    headers: dict[str, str] = {}

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def json(self) -> dict:
        return self._payload


def test_callback_url_uses_global_slack_webhook() -> None:
    request = _Request("https://example.com/")

    assert _callback_url(request, "slack", "ignored-token") == (
        "https://example.com/api/v1/triggers/webhooks/slack"
    )


def test_callback_url_keeps_tokenized_webhook_for_other_connectors() -> None:
    request = _Request("https://example.com/")

    assert _callback_url(request, "github", "abc123") == (
        "https://example.com/api/v1/triggers/webhooks/github/abc123"
    )


def test_slack_workspace_id_prefers_top_level_team_id() -> None:
    payload = {"team_id": "T123", "authorizations": [{"team_id": "T999"}]}

    assert _slack_workspace_id(payload) == "T123"


@pytest.mark.asyncio
async def test_slack_url_verification_does_not_need_connector_lookup():
    class _DB:
        async def execute(self, _query):
            raise AssertionError("url verification should not query connectors")

    response = await receive_webhook(
        _JsonRequest({"type": "url_verification", "challenge": "challenge-value"}),
        db=_DB(),
        validation_token=None,
    )

    assert response == {"challenge": "challenge-value"}


@pytest.mark.asyncio
async def test_resolve_slack_connector_by_workspace_id():
    connector = Connector(
        id=uuid4(),
        organization_id=uuid4(),
        type="slack",
        name="Slack",
        enabled=True,
        credentials={"team_id": "T123", "access_token": "token"},
        config={},
    )

    class _ScalarResult:
        def first(self):
            return connector

    class _ExecuteResult:
        def scalars(self):
            return _ScalarResult()

    class _DB:
        async def execute(self, _query):
            return _ExecuteResult()

    resolved = await _resolve_connector(
        _DB(),
        "slack",
        None,
        {"team_id": "T123", "event": {"type": "message"}},
    )

    assert resolved is not None
    assert resolved.id == connector.id
