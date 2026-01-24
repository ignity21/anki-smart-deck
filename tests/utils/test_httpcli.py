# Assuming httpcli is in src/ankinote/utils/

import aiohttp

from ankinote.utils import httpcli

# sys.path.insert(0, "/mnt/user-data/uploads")


class TestGetSession:
    """Tests for get_session() function"""

    async def test_creates_session_successfully(self) -> None:
        """Test that get_session creates a ClientSession in running event loop"""
        session = await httpcli.get_session()
        assert isinstance(session, aiohttp.ClientSession)
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

    # Note: Testing RuntimeError without event loop is difficult in pytest-asyncio
    # as asyncio.run() creates its own event loop. This test is commented out.
    # The error handling is present in the code but hard to test in this context.


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
        # Since session was already closed, close_session doesn't set _session to None
        # But _session should still point to a closed session
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
