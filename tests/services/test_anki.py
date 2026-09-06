"""Tests for the Anki service layer."""

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest
from pytest_mock import MockerFixture

from ankinote.services.anki import (
    AnkiConnectClient,
    AnkiConnectError,
    AnkiResponseError,
    AnkiTransportError,
    ModelClient,
    ModelNotFound,
    NoteClient,
    TemplateUpsert,
)


async def test_note_lookup_scopes_model_and_escapes_literal_front():
    invoke = AsyncMock(return_value=[123])
    client = NoteClient(StubInvoker(invoke))
    result = await client.find(
        "AINote::STEM",
        {"front": 'What is "x*y_1"?'},
        model_name="AINote STEM Formula",
    )
    assert result == 123
    query = invoke.await_args.kwargs["params"]["query"]
    assert 'note:"AINote STEM Formula"' in query
    assert r"x\*y\_1" in query
    assert r"\"x" in query


class StubInvoker:
    """Typed stub for model client tests."""

    def __init__(self, mock_invoke: AsyncMock) -> None:
        self._mock_invoke = mock_invoke

    async def _invoke(self, action: str, params: dict[str, object] | None = None):
        return await self._mock_invoke(action, params=params)


def _build_model_payload(name: str = "AINote Word") -> dict[str, object]:
    """Create a minimal valid Anki model payload for tests."""
    return {
        "id": 1,
        "name": name,
        "type": 0,
        "sortf": 0,
        "did": None,
        "tmpls": [
            {
                "id": 11,
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{Back}}",
                "ord": 0,
            }
        ],
        "flds": [
            {
                "id": 21,
                "name": "Front",
                "description": "",
                "ord": 0,
                "font": "Arial",
                "size": 20,
                "plainText": False,
                "collapsed": True,
                "excludeFromSearch": False,
            }
        ],
        "css": ".card {}",
        "latexPre": "",
        "latexPost": "",
        "latexsvg": False,
        "req": [],
    }


class TestModelClient:
    """Contract tests for model lookup behavior."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_one_match(self):
        invoke = AsyncMock(return_value=[_build_model_payload()])
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        assert await client.exists("AINote Word") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_zero_matches(self):
        invoke = AsyncMock(return_value=[])
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        assert await client.exists("AINote Word") is False

    @pytest.mark.asyncio
    async def test_exists_propagates_service_errors(self):
        invoke = AsyncMock(side_effect=AnkiConnectError("boom"))
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        with pytest.raises(AnkiConnectError, match="boom"):
            await client.exists("AINote Word")

    @pytest.mark.asyncio
    async def test_exists_raises_on_multiple_matches(self):
        invoke = AsyncMock(
            return_value=[
                _build_model_payload("AINote Word"),
                _build_model_payload("AINote Word"),
            ]
        )
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        with pytest.raises(AnkiResponseError, match="at most one model"):
            await client.exists("AINote Word")

    @pytest.mark.asyncio
    async def test_get_returns_model_for_one_match(self):
        invoke = AsyncMock(return_value=[_build_model_payload()])
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        model = await client.get("AINote Word")

        assert model is not None
        assert model.name == "AINote Word"
        assert model.fields[0].name == "Front"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_zero_matches(self):
        invoke = AsyncMock(return_value=[])
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        assert await client.get("AINote Word") is None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_anki_reports_model_not_found(self):
        invoke = AsyncMock(
            side_effect=AnkiConnectError("model was not found: AINote Word")
        )
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        assert await client.get("AINote Word") is None

    @pytest.mark.asyncio
    async def test_require_raises_model_not_found(self):
        invoke = AsyncMock(return_value=[])
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        with pytest.raises(ModelNotFound, match="AINote Word"):
            await client.require("AINote Word")

    @pytest.mark.asyncio
    async def test_update_templates_updates_existing_template_by_name(self):
        invoke = AsyncMock(
            side_effect=[
                {"Recognition": {"Front": "{{Front}}", "Back": "{{Back}}"}},
                None,
            ]
        )
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        await client.update_templates(
            "AINote Word",
            [
                TemplateUpsert(
                    name="Recognition",
                    question_format="{{Word}}",
                    answer_format="{{Answer}}",
                )
            ],
        )

        assert invoke.await_args_list == [
            call("modelTemplates", params={"modelName": "AINote Word"}),
            call(
                "updateModelTemplates",
                params={
                    "model": {
                        "name": "AINote Word",
                        "templates": {
                            "Recognition": {
                                "Front": "{{Word}}",
                                "Back": "{{Answer}}",
                            }
                        },
                    }
                },
            ),
        ]

    @pytest.mark.asyncio
    async def test_update_templates_adds_new_template_by_name(self):
        invoke = AsyncMock(
            side_effect=[
                {"Recognition": {"Front": "{{Front}}", "Back": "{{Back}}"}},
                None,
            ]
        )
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        await client.update_templates(
            "AINote Word",
            [
                TemplateUpsert(
                    name="Recall",
                    question_format="{{Back}}",
                    answer_format="{{Front}}",
                )
            ],
        )

        assert invoke.await_args_list == [
            call("modelTemplates", params={"modelName": "AINote Word"}),
            call(
                "modelTemplateAdd",
                params={
                    "modelName": "AINote Word",
                    "template": {
                        "Name": "Recall",
                        "Front": "{{Back}}",
                        "Back": "{{Front}}",
                    },
                },
            ),
        ]

    @pytest.mark.asyncio
    async def test_update_templates_renames_then_updates(self):
        invoke = AsyncMock(
            side_effect=[
                {"Recognition": {"Front": "{{Front}}", "Back": "{{Back}}"}},
                None,
                None,
            ]
        )
        stub = StubInvoker(invoke)
        client = ModelClient(stub)

        await client.update_templates(
            "AINote Word",
            [
                TemplateUpsert(
                    name="Recognition 2",
                    previous_name="Recognition",
                    question_format="{{Word}}",
                    answer_format="{{Answer}}",
                )
            ],
        )

        assert invoke.await_args_list == [
            call("modelTemplates", params={"modelName": "AINote Word"}),
            call(
                "modelTemplateRename",
                params={
                    "modelName": "AINote Word",
                    "oldTemplateName": "Recognition",
                    "newTemplateName": "Recognition 2",
                },
            ),
            call(
                "updateModelTemplates",
                params={
                    "model": {
                        "name": "AINote Word",
                        "templates": {
                            "Recognition 2": {
                                "Front": "{{Word}}",
                                "Back": "{{Answer}}",
                            }
                        },
                    }
                },
            ),
        ]


class TestAnkiConnectInvoke:
    """Boundary tests for raw AnkiConnect responses."""

    @pytest.mark.asyncio
    async def test_invoke_wraps_transport_errors(self, mocker: MockerFixture):
        client = AnkiConnectClient()
        request = httpx.Request("POST", "http://localhost:8765")
        mocker.patch(
            "ankinote.services.anki.post",
            new=AsyncMock(side_effect=httpx.ConnectError("offline", request=request)),
        )

        with pytest.raises(AnkiTransportError, match="Failed to reach AnkiConnect"):
            await client._invoke("modelNames")

    @pytest.mark.asyncio
    async def test_invoke_raises_on_invalid_json(self, mocker: MockerFixture):
        client = AnkiConnectClient()
        response = Mock()
        response.json.side_effect = ValueError("bad json")
        mocker.patch(
            "ankinote.services.anki.post", new=AsyncMock(return_value=response)
        )

        with pytest.raises(AnkiResponseError, match="invalid JSON"):
            await client._invoke("modelNames")

    @pytest.mark.asyncio
    async def test_invoke_raises_on_missing_result_or_error_keys(
        self, mocker: MockerFixture
    ):
        client = AnkiConnectClient()
        response = Mock()
        response.json.return_value = {"result": []}
        mocker.patch(
            "ankinote.services.anki.post", new=AsyncMock(return_value=response)
        )

        with pytest.raises(
            AnkiResponseError, match="include both 'error' and 'result'"
        ):
            await client._invoke("modelNames")

    @pytest.mark.asyncio
    async def test_invoke_raises_on_business_error(self, mocker: MockerFixture):
        client = AnkiConnectClient()
        response = Mock()
        response.json.return_value = {"result": None, "error": "model was not found"}
        mocker.patch(
            "ankinote.services.anki.post", new=AsyncMock(return_value=response)
        )

        with pytest.raises(AnkiConnectError, match="model was not found"):
            await client._invoke("addNote")
