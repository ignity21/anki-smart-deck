import asyncio

import httpx
from loguru import logger

_client: httpx.AsyncClient | None = None

_RETRY_MAX_ATTEMPTS = 4
_RETRYABLE_EXCEPTIONS = (
    httpx.RequestError,
    asyncio.TimeoutError,
)


def init_session() -> httpx.AsyncClient:
    """Initialize the global httpx client with connection pooling.

    Uses a single shared :class:`httpx.AsyncClient` across the application
    to reuse TCP connections and reduce overhead. Must be called within a
    running asyncio event loop.
    """
    global _client
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError("init_session() must be called within a running event loop")

    if _client is None or _client.is_closed:
        logger.debug("Initializing httpx client")
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            ),
        )
    return _client


def _get_client_or_raise() -> httpx.AsyncClient:
    """Return the active client or raise if not initialized."""
    if _client is None or _client.is_closed:
        raise RuntimeError("Client not initialized. Call init_session() first.")
    return _client


def get_session() -> httpx.AsyncClient:
    """Return the current httpx client.

    Raises:
        RuntimeError: If :func:`init_session` has not been called.
    """
    return _get_client_or_raise()


async def close_session() -> None:
    """Close the global httpx client, if one is active.

    Safe to call even if the client was never initialized or already closed.
    """
    client = _client
    if client is not None and not client.is_closed:
        await client.aclose()
        logger.debug("httpx client closed")


async def request(method: str, url: str, **kwargs) -> httpx.Response:
    """Send an HTTP request with automatic retry on transient errors.

    Retries up to :const:`_RETRY_MAX_ATTEMPTS` times with exponential
    backoff (1 s, 2 s, 4 s) on transport-level and timeout errors.

    Args:
        method: HTTP method (``"GET"``, ``"POST"``, etc.).
        url: Target URL.
        **kwargs: Additional arguments forwarded to :meth:`httpx.AsyncClient.request`.

    Returns:
        The :class:`httpx.Response`.

    Raises:
        RuntimeError: If the client has not been initialized.
        httpx.RequestError: If all retry attempts fail on transport-level errors.
    """
    client = _get_client_or_raise()
    for attempt in range(_RETRY_MAX_ATTEMPTS):
        try:
            return await client.request(method, url, **kwargs)
        except _RETRYABLE_EXCEPTIONS as exc:
            if attempt == _RETRY_MAX_ATTEMPTS - 1:
                logger.error(
                    f"Request failed after {_RETRY_MAX_ATTEMPTS} attempts: {exc}"
                )
                raise
            await asyncio.sleep(1 * (2**attempt))
    raise RuntimeError("Unreachable code reached in request")


async def get(url: str, **kwargs) -> httpx.Response:
    """Send a GET request with automatic retry on transient errors.

    See :func:`request` for retry behavior.
    """
    return await request("GET", url, **kwargs)


async def post(url: str, **kwargs) -> httpx.Response:
    """Send a POST request with automatic retry on transient errors.

    See :func:`request` for retry behavior.
    """
    return await request("POST", url, **kwargs)


__all__ = [
    "init_session",
    "get_session",
    "close_session",
    "request",
    "get",
    "post",
]
