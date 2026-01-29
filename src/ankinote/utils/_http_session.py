import asyncio

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse, ClientSession
from aiohttp.client_exceptions import ClientError, ServerDisconnectedError
from loguru import logger


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


class HttpClient:
    """
    A manager for a singleton ClientSession that supports lazy loading
    and automatic cleanup via async context management.
    """

    def __init__(self):
        self._session: ClientSession | None = None

    def get_session(self) -> ClientSession:
        """
        Get the singleton ClientSession.
        Initializes a new session lazily if it doesn't exist or has been closed.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                "get_session() must be called within a running event loop"
            )

        if self._session is None or self._session.closed:
            logger.debug("Initializing singleton ClientSession (Lazy Load)")
            self._session = ClientSession(
                raise_for_status=True, middlewares=[retry_middleware]
            )
        return self._session

    async def __aenter__(self):
        """
        Entry point for the async context manager.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the session is closed gracefully when exiting the context.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("ClientSession closed gracefully via context manager")
        self._session = None


# Global instance to be used across the application
http = HttpClient()
