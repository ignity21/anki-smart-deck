import asyncio

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse, ClientSession
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


async def get_session() -> ClientSession:
    """
    Get the singleton ClientSession.
    Initializes a new session if it doesn't exist or has been closed.
    """
    global _session
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError("get_session() must be called within a running event loop")

    if _session is None or _session.closed:
        # Created lazily within the running event loop
        _session = ClientSession(raise_for_status=True, middlewares=[retry_middleware])
    return _session


async def close_session() -> None:
    """
    Ensure the session is closed gracefully before the application exits.
    """
    global _session
    if _session and not _session.closed:
        await _session.close()
        # As the official Q&A suggests, give some time for cleanup
        # await asyncio.sleep(0.250)
        _session = None
