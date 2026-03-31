import asyncio

from aiohttp import (
    ClientHandlerType,
    ClientRequest,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    TCPConnector,
)
from aiohttp.client_exceptions import ClientError, ServerDisconnectedError
from loguru import logger

_session: ClientSession | None = None


async def retry_middleware(
    req: ClientRequest, handler: ClientHandlerType
) -> ClientResponse:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await handler(req)
        except (ClientError, ServerDisconnectedError, asyncio.TimeoutError) as exc:
            if attempt == max_retries - 1:
                logger.error(f"Request failed after {max_retries} attempts: {exc}")
                raise
            await asyncio.sleep(1 * (2**attempt))  # Exponential backoff
    assert False, "Unreachable code reached in retry_middleware"


def init_session() -> ClientSession:
    """Initializes a new session(create connection pool)"""
    global _session
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError("get_session() must be called within a running event loop")

    if _session is None or _session.closed:
        logger.debug("Initializing client session")
        _session = ClientSession(
            raise_for_status=True,
            middlewares=[retry_middleware],
            timeout=ClientTimeout(total=60),
            connector=TCPConnector(
                limit=10,
                limit_per_host=5,
                enable_cleanup_closed=True,
            ),
        )
    return _session


def _is_session_alive() -> ClientSession:
    """Ensures that a session is initialized and returns it"""
    if _session is None or _session.closed:
        raise RuntimeError("Session not initialized. Call init_session() first.")
    return _session


async def close_session():
    session = _is_session_alive()
    await session.close()
    logger.debug("client session closed")


def get_session() -> ClientSession:
    """Returns the current session"""
    session = _is_session_alive()
    return session


__all__ = [
    "init_session",
    "get_session",
    "close_session",
]
