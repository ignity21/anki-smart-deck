"""Application save boundaries for the direct backend."""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar

from ankinote.services.anki import AnkiCollectionClient
from ankinote.services.anki_direct import DirectCollectionClient
from ankinote.services.anki_sync import SyncWriteBlocked

_save_blocked: ContextVar[Callable[[], Awaitable[None]] | None] = ContextVar(
    "anki_save_blocked", default=None
)
_saved: ContextVar[Callable[[], None] | None] = ContextVar("anki_saved", default=None)


@contextmanager
def recoverable_save(
    on_blocked: Callable[[], Awaitable[None]],
    on_saved: Callable[[], None] | None = None,
) -> Iterator[None]:
    """Keep generated data in its task while the UI resolves write admission."""
    token = _save_blocked.set(on_blocked)
    saved_token = _saved.set(on_saved)
    try:
        yield
    finally:
        _save_blocked.reset(token)
        _saved.reset(saved_token)


@asynccontextmanager
async def anki_write_batch(client: AnkiCollectionClient) -> AsyncIterator[None]:
    """Serialize a complete save with sync; connect clients need no local lock."""
    if isinstance(client, DirectCollectionClient):
        async with AsyncExitStack() as stack:
            while True:
                try:
                    await stack.enter_async_context(client._runtime.write_batch())
                except SyncWriteBlocked:
                    if (on_blocked := _save_blocked.get()) is None:
                        raise
                    await on_blocked()
                else:
                    break
            yield
            if (on_saved := _saved.get()) is not None:
                on_saved()
    else:
        yield
