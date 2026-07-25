"""Tests for the httpx-based HTTP client module."""

import asyncio
import json
from unittest.mock import AsyncMock, call

import httpx
import pytest
from pytest_mock import MockerFixture

from ankinote.utils.httpcli import (
    _RETRY_MAX_ATTEMPTS,
    _RETRYABLE_EXCEPTIONS,
    close_session,
    get,
    get_session,
    init_session,
    post,
    request,
)


@pytest.fixture(autouse=True)
async def cleanup_session():
    """Ensure no leftover session between tests."""
    await close_session()
    yield
    await close_session()


class TestSessionLifecycle:
    """Tests for init_session / get_session / close_session."""

    @pytest.mark.asyncio
    async def test_init_creates_session(self):
        """init_session() creates a new AsyncClient."""
        client = init_session()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

    @pytest.mark.asyncio
    async def test_get_session_returns_same_instance(self):
        """get_session() returns the same instance as init_session()."""
        client1 = init_session()
        client2 = get_session()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_session(self):
        """close_session() closes the client."""
        client = init_session()
        assert not client.is_closed
        await close_session()
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_close_session_idempotent(self):
        """close_session() is safe to call multiple times."""
        await close_session()  # No session yet — should not raise
        init_session()
        await close_session()
        await close_session()  # Already closed — should not raise

    @pytest.mark.asyncio
    async def test_init_after_close_creates_new(self):
        """init_session() after close creates a new client."""
        client1 = init_session()
        await close_session()
        client2 = init_session()
        assert client1 is not client2
        assert not client2.is_closed

    def test_init_requires_event_loop(self):
        """init_session() raises when called outside an event loop."""
        with pytest.raises(
            RuntimeError, match="must be called within a running event loop"
        ):
            init_session()

    @pytest.mark.asyncio
    async def test_get_session_raises_before_init(self):
        """get_session() raises if init_session() was never called."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_session()


class TestRequestHelpers:
    """Tests for request / get / post helpers."""

    @pytest.mark.asyncio
    async def test_get_passes_method(self, mocker: MockerFixture):
        """get() calls request() with method='GET'."""
        mock = mocker.patch("ankinote.utils.httpcli.request", new_callable=AsyncMock)
        await get("http://example.com")
        mock.assert_awaited_once_with("GET", "http://example.com")

    @pytest.mark.asyncio
    async def test_post_passes_method(self, mocker: MockerFixture):
        """post() calls request() with method='POST'."""
        mock = mocker.patch("ankinote.utils.httpcli.request", new_callable=AsyncMock)
        await post("http://example.com", json={"key": "value"})
        mock.assert_awaited_once_with(
            "POST", "http://example.com", json={"key": "value"}
        )

    @pytest.mark.asyncio
    async def test_request_passes_kwargs(self, mocker: MockerFixture):
        """request() forwards kwargs to the underlying client."""
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(200)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        mocker.patch("ankinote.utils.httpcli._get_client_or_raise", return_value=client)

        resp = await request("POST", "http://example.com", json={"a": 1})
        assert resp.status_code == 200

        sent = captured["request"]
        assert sent.method == "POST"
        assert str(sent.url) == "http://example.com"
        assert sent.headers["content-type"] == "application/json"
        assert json.loads(sent.content) == {"a": 1}
        await client.aclose()

    @pytest.mark.asyncio
    async def test_request_raises_before_init(self):
        """request() raises if client is not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await request("GET", "http://example.com")


class TestRetry:
    """Tests for retry logic in request()."""

    @pytest.fixture
    def failing_transport(self):
        """A transport that fails N times then succeeds."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.ConnectError("Connection refused", request=request)
            return httpx.Response(200, json={"ok": True})

        return handler

    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds(
        self, mocker: MockerFixture, failing_transport
    ):
        """request() retries on transport errors and eventually succeeds."""
        client = httpx.AsyncClient(transport=httpx.MockTransport(failing_transport))
        mocker.patch("ankinote.utils.httpcli._get_client_or_raise", return_value=client)
        mocker.patch("ankinote.utils.httpcli.asyncio.sleep", new_callable=AsyncMock)

        resp = await request("GET", "http://example.com")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        await client.aclose()

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, mocker: MockerFixture):
        """request() raises after exhausting all retry attempts."""

        def always_fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Always fails", request=request)

        client = httpx.AsyncClient(transport=httpx.MockTransport(always_fail))
        mocker.patch("ankinote.utils.httpcli._get_client_or_raise", return_value=client)
        sleep_mock = mocker.patch(
            "ankinote.utils.httpcli.asyncio.sleep", new_callable=AsyncMock
        )

        with pytest.raises(httpx.ConnectError, match="Always fails"):
            await request("GET", "http://example.com")

        # Should sleep (RETRY_MAX_ATTEMPTS - 1) times with exponential
        # backoff (1 s, 2 s, 4 s)
        assert sleep_mock.await_count == _RETRY_MAX_ATTEMPTS - 1
        sleep_mock.assert_has_awaits([call(1), call(2), call(4)])
        await client.aclose()

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, mocker: MockerFixture):
        """request() returns immediately without retry on success."""

        def success(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        client = httpx.AsyncClient(transport=httpx.MockTransport(success))
        mocker.patch("ankinote.utils.httpcli._get_client_or_raise", return_value=client)
        sleep_mock = mocker.patch(
            "ankinote.utils.httpcli.asyncio.sleep", new_callable=AsyncMock
        )

        resp = await request("GET", "http://example.com")
        assert resp.status_code == 200
        sleep_mock.assert_not_awaited()
        await client.aclose()


class TestRetryableExceptions:
    """Verify the retryable exceptions tuple."""

    def test_includes_httpx_request_error(self):
        assert httpx.RequestError in _RETRYABLE_EXCEPTIONS

    def test_includes_asyncio_timeout(self):
        assert asyncio.TimeoutError in _RETRYABLE_EXCEPTIONS
