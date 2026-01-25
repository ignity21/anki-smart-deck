import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from aiohttp import ClientError, ClientResponse, ClientSession, ServerDisconnectedError

from ankinote.utils import httpcli


class TestGetSession:
    """Tests for get_session() function"""

    async def test_creates_session_successfully(self) -> None:
        """Test that get_session creates a ClientSession in running event loop"""
        session = await httpcli.get_session()
        assert isinstance(session, ClientSession)
        assert not session.closed
        await httpcli.close_session()

    async def test_returns_singleton_session(self) -> None:
        """Test that multiple calls return the same session instance"""
        session1 = await httpcli.get_session()
        session2 = await httpcli.get_session()
        assert session1 is session2
        await httpcli.close_session()

    async def test_creates_new_session_after_close(self) -> None:
        """Test that a new session is created if previous one was closed"""
        session1 = await httpcli.get_session()
        await httpcli.close_session()

        session2 = await httpcli.get_session()
        assert session1 is not session2
        assert not session2.closed
        await httpcli.close_session()

    async def test_session_has_retry_middleware(self) -> None:
        """Test that session is created with retry middleware"""
        session = await httpcli.get_session()
        # Check that middlewares are configured
        assert len(session._middlewares) > 0
        await httpcli.close_session()

    async def test_session_has_raise_for_status(self) -> None:
        """Test that session is created with raise_for_status=True"""
        session = await httpcli.get_session()
        assert session._raise_for_status is True
        await httpcli.close_session()


class TestCloseSession:
    """Tests for close_session() function"""

    async def test_closes_open_session(self) -> None:
        """Test that close_session successfully closes an open session"""
        session = await httpcli.get_session()
        assert not session.closed

        await httpcli.close_session()
        assert session.closed
        assert httpcli._session is None

    async def test_handles_already_closed_session(self) -> None:
        """Test that close_session handles already closed session gracefully"""
        session = await httpcli.get_session()
        await session.close()

        # Should not raise error
        await httpcli.close_session()
        # Session was already closed, so _session won't be set to None
        assert httpcli._session is not None
        assert httpcli._session.closed

        # Clean up for next test
        httpcli._session = None

    async def test_handles_none_session(self) -> None:
        """Test that close_session handles None session gracefully"""
        httpcli._session = None

        # Should not raise error
        await httpcli.close_session()
        assert httpcli._session is None

    async def test_multiple_close_calls(self) -> None:
        """Test that multiple close_session calls don't cause errors"""
        await httpcli.get_session()

        await httpcli.close_session()
        await httpcli.close_session()
        await httpcli.close_session()

        assert httpcli._session is None


class TestRetryMiddleware:
    """Tests for retry_middleware function"""

    async def test_successful_request_on_first_attempt(self) -> None:
        """Test that successful requests don't trigger retries"""
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200

        async def mock_handler(_) -> ClientResponse:
            return mock_response

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        result = await httpcli.retry_middleware(mock_request, mock_handler)
        assert result == mock_response

    async def test_retries_on_client_error(self) -> None:
        """Test that ClientError triggers retries with exponential backoff"""
        call_count = 0

        async def mock_handler(_) -> ClientResponse:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ClientError("Connection error")
            mock_response = Mock(spec=ClientResponse)
            mock_response.status = 200
            return mock_response

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await httpcli.retry_middleware(mock_request, mock_handler)

            assert call_count == 3
            assert mock_sleep.call_count == 2
            # Check exponential backoff: 1s, 2s
            mock_sleep.assert_any_await(1)
            mock_sleep.assert_any_await(2)

    async def test_retries_on_server_disconnected_error(self) -> None:
        """Test that ServerDisconnectedError triggers retries"""
        call_count = 0

        async def mock_handler(_) -> ClientResponse:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServerDisconnectedError("Server disconnected")
            mock_response = Mock(spec=ClientResponse)
            mock_response.status = 200
            return mock_response

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await httpcli.retry_middleware(mock_request, mock_handler)

            assert call_count == 2
            assert mock_sleep.call_count == 1
            mock_sleep.assert_awaited_once_with(1)

    async def test_retries_on_timeout_error(self) -> None:
        """Test that TimeoutError triggers retries"""
        call_count = 0

        async def mock_handler(_) -> ClientResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Request timeout")
            mock_response = Mock(spec=ClientResponse)
            mock_response.status = 200
            return mock_response

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await httpcli.retry_middleware(mock_request, mock_handler)

            assert call_count == 2
            mock_sleep.assert_awaited_once_with(1)

    async def test_raises_after_max_retries(self) -> None:
        """Test that exception is raised after max retries exhausted"""

        async def mock_handler(_) -> ClientResponse:
            raise ClientError("Persistent error")

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ClientError, match="Persistent error"):
                await httpcli.retry_middleware(mock_request, mock_handler)

    async def test_exponential_backoff_timing(self) -> None:
        """Test that retry delays follow exponential backoff: 1s, 2s, 4s"""
        call_count = 0

        async def mock_handler(_) -> ClientResponse:
            nonlocal call_count
            call_count += 1
            raise ClientError(f"Error {call_count}")

        mock_request = Mock(spec=aiohttp.ClientRequest)
        mock_request.url = "http://example.com"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ClientError):
                await httpcli.retry_middleware(mock_request, mock_handler)

            # Should have 3 attempts, 2 sleeps (before 2nd and 3rd attempts)
            assert call_count == 3
            assert mock_sleep.call_count == 2

            # Verify exact delays: 1 * 2^0 = 1, 1 * 2^1 = 2
            calls = mock_sleep.await_args_list
            assert calls[0][0][0] == 1  # First retry: 1s
            assert calls[1][0][0] == 2  # Second retry: 2s
