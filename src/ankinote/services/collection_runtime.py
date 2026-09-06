"""Single-threaded runtime for an in-process Anki collection.

Anki's ``Collection`` is not thread-safe and must be touched from one thread for
its whole lifetime. This runtime owns that thread: the asyncio layer submits
plain callables that receive the live ``Collection`` and run serially on the
worker, and only their return values (never raw Anki objects) cross back.

The concrete ``anki`` package is imported lazily so importing this module does
not require the ``headless`` extra.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Callable
from typing import Any, Protocol

_DEFAULT_CLOSE_TIMEOUT = 30.0


class CollectionRuntimeError(Exception):
    """Raised for misuse of the runtime lifecycle."""


class CollectionInUseError(CollectionRuntimeError):
    """Raised when the collection is already open in another process."""


class CollectionOpener(Protocol):
    """Opens a collection at ``path`` and returns the live object."""

    def __call__(self, path: str, /) -> Any: ...


def _default_opener(path: str, /) -> Any:
    from anki.collection import Collection

    return Collection(path)


def _translate_open_error(exc: BaseException, path: str) -> BaseException:
    """Map Anki's lock error onto :class:`CollectionInUseError`."""
    if type(exc).__name__ == "DBError" or "already open" in str(exc).lower():
        return CollectionInUseError(
            f"The Anki collection at {path} is in use by another process "
            f"(Anki Desktop or another ankinote process)."
        )
    return exc


class _Job:
    __slots__ = ("_fn", "_future", "_loop")

    def __init__(
        self,
        fn: Callable[[Any], Any],
        future: asyncio.Future[Any],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._fn = fn
        self._future = future
        self._loop = loop

    def run(self, collection: Any) -> None:
        try:
            result = self._fn(collection)
        except BaseException as exc:
            self._loop.call_soon_threadsafe(self._set_exception, exc)
        else:
            self._loop.call_soon_threadsafe(self._set_result, result)

    def _set_result(self, result: Any) -> None:
        if not self._future.cancelled():
            self._future.set_result(result)

    def _set_exception(self, exc: BaseException) -> None:
        if not self._future.cancelled():
            self._future.set_exception(exc)


class CollectionRuntime:
    """Owns one worker thread and the ``Collection`` living on it."""

    def __init__(
        self,
        path: str,
        *,
        opener: CollectionOpener | None = None,
        close_timeout: float = _DEFAULT_CLOSE_TIMEOUT,
    ) -> None:
        self._path = path
        self._opener: CollectionOpener = opener or _default_opener
        self._close_timeout = close_timeout
        self._queue: queue.SimpleQueue[_Job | None] = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._collection: Any = None
        self._opened = threading.Event()
        self._open_error: BaseException | None = None
        self._closed = False

    @property
    def path(self) -> str:
        return self._path

    async def open(self) -> None:
        """Start the worker and open the collection, or raise if it cannot."""
        if self._thread is not None:
            raise CollectionRuntimeError("runtime already opened")
        self._thread = threading.Thread(
            target=self._worker, name="anki-collection", daemon=True
        )
        self._thread.start()
        await asyncio.get_running_loop().run_in_executor(None, self._opened.wait)
        if self._open_error is not None:
            self._thread.join(self._close_timeout)
            self._thread = None
            raise self._open_error

    async def submit[T](self, fn: Callable[[Any], T]) -> T:
        """Run ``fn(collection)`` on the worker thread and return its result."""
        if self._thread is None or self._closed:
            raise CollectionRuntimeError("runtime is not open")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()
        self._queue.put(_Job(fn, future, loop))
        return await future

    async def close(self) -> None:
        """Stop the worker, close the collection, and join within the timeout."""
        if self._thread is None:
            return
        self._closed = True
        self._queue.put(None)
        thread = self._thread
        await asyncio.get_running_loop().run_in_executor(
            None, thread.join, self._close_timeout
        )
        if thread.is_alive():
            raise CollectionRuntimeError(
                f"anki-collection worker did not exit within {self._close_timeout}s"
            )
        self._thread = None

    def _worker(self) -> None:
        try:
            self._collection = self._opener(self._path)
        except BaseException as exc:
            self._open_error = _translate_open_error(exc, self._path)
            self._opened.set()
            return
        self._opened.set()

        try:
            while True:
                job = self._queue.get()
                if job is None:
                    break
                job.run(self._collection)
        finally:
            try:
                self._collection.close()
            finally:
                self._collection = None
