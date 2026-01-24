import asyncio

import aiohttp

_session: aiohttp.ClientSession | None = None


async def get_session() -> aiohttp.ClientSession:
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
        _session = aiohttp.ClientSession()
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
