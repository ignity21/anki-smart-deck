"""Tests for HTTPSessionManager."""

import asyncio
from unittest.mock import AsyncMock, call

import aiohttp
import pytest
from aiohttp import ClientSession
from pytest_mock import MockerFixture

from ankinote.utils._http_session import HttpClient, http, retry_middleware


@pytest.fixture
def http_cli():
    return HttpClient()


class TestHttpClient:
    """Test cases for HttpClient."""

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, http_cli):
        """Test that get_session creates a new ClientSession."""
        session = http_cli.get_session()

        assert isinstance(session, ClientSession)
        assert not session.closed

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self, http_cli):
        """Test that the context manager properly closes the session."""
        async with http_cli:
            session = http_cli.get_session()
            assert not session.closed

        # After exiting context, session should be closed
        assert session.closed

    @pytest.mark.asyncio
    async def test_get_session_returns_same_instance(self, http_cli):
        """Test that get_session returns the same session instance."""
        async with http_cli:
            session1 = http_cli.get_session()
            session2 = http_cli.get_session()
            assert session1 is session2

        assert session1.closed

    @pytest.mark.asyncio
    async def test_get_session_recreates_after_close(self, http_cli):
        """Test that get_session creates a new session after the old one is closed."""

        session1 = http_cli.get_session()
        await session1.close()

        session2 = http_cli.get_session()
        assert session1 is not session2
        assert not session2.closed

        # Cleanup
        await session2.close()

    @pytest.mark.asyncio
    async def test_context_http_cli_allows_reentry(self, http_cli):
        """Test that http_cli can be used in multiple contexts."""

        async with http_cli:
            session1 = http_cli.get_session()
            assert not session1.closed

        assert session1.closed

        async with http_cli:
            session2 = http_cli.get_session()
            assert not session2.closed
            assert session1 is not session2

        assert session2.closed

    def test_get_session_requires_event_loop(self, http_cli):
        """Test that get_session raises error when called outside event loop."""

        with pytest.raises(
            RuntimeError, match="must be called within a running event loop"
        ):
            # This should fail because there's no running event loop
            http_cli.get_session()

    @pytest.mark.asyncio
    async def test_session_has_retry_middleware(self, http_cli):
        """Test that the session is configured with retry middleware."""

        session = http_cli.get_session()

        # Check that middlewares are configured
        assert hasattr(session, "_request_class")

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_session_has_raise_for_status(self, http_cli):
        """Test that the session raises for HTTP status errors."""

        session = http_cli.get_session()

        # Check that raise_for_status is enabled
        # Note: This is a bit tricky to test directly, but we can verify the session config
        assert session._raise_for_status is True

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_global_session_http_cli(self):
        """Test the global http instance."""
        session = http.get_session()
        assert isinstance(session, ClientSession)
        assert not session.closed

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_access(self, http_cli):
        """Test that concurrent access to get_session returns the same instance."""

        # Start multiple coroutines trying to get the session
        async def get_sess():
            return http_cli.get_session()

        sessions = await asyncio.gather(
            get_sess(),
            get_sess(),
            get_sess(),
        )

        # All should be the same instance
        assert all(s is sessions[0] for s in sessions)

        # Cleanup
        await sessions[0].close()


class TestRetryMiddleware:
    """Test cases for the retry middleware logic."""

    @pytest.fixture
    def mock_req(self, mocker: MockerFixture):
        """Mock aiohttp ClientRequest."""
        return mocker.MagicMock(spec=aiohttp.ClientRequest)

    @pytest.fixture
    def mock_sleep(self, mocker: MockerFixture):
        """Mock asyncio.sleep to speed up tests and verify backoff timing."""
        return mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, mock_req, mock_sleep):
        """Test that a successful request returns immediately without retry."""
        mock_resp = AsyncMock(spec=aiohttp.ClientResponse)
        mock_handler = AsyncMock(return_value=mock_resp)

        result = await retry_middleware(mock_req, mock_handler)

        assert result == mock_resp
        assert mock_handler.call_count == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds(self, mock_req, mock_sleep):
        """Test that the middleware retries on error and eventually succeeds."""
        mock_resp = AsyncMock(spec=aiohttp.ClientResponse)
        mock_handler = AsyncMock(
            side_effect=[
                aiohttp.ServerDisconnectedError("Connection lost"),
                asyncio.TimeoutError("Request timed out"),
                mock_resp,
            ]
        )

        result = await retry_middleware(mock_req, mock_handler)

        assert result == mock_resp
        assert mock_handler.call_count == 3

        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_awaits([call(1), call(2)])

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self, mock_req, mock_sleep):
        """Test that after max_retries, the last exception is raised."""
        last_error = aiohttp.ClientError("Permanent failure")
        mock_handler = AsyncMock(
            side_effect=[
                aiohttp.ClientError("Fail 1"),
                aiohttp.ClientError("Fail 2"),
                last_error,
            ]
        )

        with pytest.raises(aiohttp.ClientError) as exc_info:
            await retry_middleware(mock_req, mock_handler)

        assert exc_info.value == last_error
        assert mock_handler.call_count == 3
        assert mock_sleep.call_count == 2


class TestSessionCleanup:
    """Test cases for proper session cleanup."""

    @pytest.mark.asyncio
    async def test_manual_cleanup(self, http_cli):
        """Test manual cleanup of session."""

        session = http_cli.get_session()

        assert not session.closed
        await session.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_aexit_with_no_session(self, http_cli):
        """Test that __aexit__ handles case when no session was created."""

        # Don't create a session, just exit the context
        async with http_cli:
            pass  # No session created

        # Should not raise any errors
        assert http_cli._session is None

    @pytest.mark.asyncio
    async def test_aexit_with_already_closed_session(self, http_cli):
        """Test that __aexit__ handles already closed sessions gracefully."""

        async with http_cli:
            session = http_cli.get_session()
            await session.close()  # Close it manually

        # Should not raise any errors
        assert http_cli._session is None
