"""Tests for the single-threaded Anki collection runtime."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from ankinote.services.collection_runtime import (
    CollectionInUseError,
    CollectionRuntime,
    CollectionRuntimeError,
)

pytestmark = pytest.mark.asyncio


class FakeCollection:
    def __init__(self, path: str) -> None:
        self.path = path
        self.closed = False
        self.opened_on = threading.current_thread().name

    def close(self) -> None:
        self.closed = True


class DBError(Exception):
    """Stands in for anki.errors.DBError (matched by class name)."""


async def test_work_runs_on_one_worker_thread_and_returns_plain_values() -> None:
    runtime = CollectionRuntime("/x", opener=FakeCollection)
    await runtime.open()
    try:
        main_thread = threading.current_thread().name
        seen: list[object] = []

        def job(col: object) -> str:
            seen.append(col)
            return f"{threading.current_thread().name}"

        name_a = await runtime.submit(job)
        name_b = await runtime.submit(job)

        assert name_a == name_b == "anki-collection" != main_thread
        assert isinstance(seen[0], FakeCollection) and seen[0] is seen[1]
    finally:
        await runtime.close()
    assert seen[0].closed is True  # type: ignore[union-attr]


async def test_exception_in_job_propagates_without_killing_worker() -> None:
    runtime = CollectionRuntime("/x", opener=FakeCollection)
    await runtime.open()
    try:

        def boom(_col: object) -> None:
            raise ValueError("kaboom")

        with pytest.raises(ValueError, match="kaboom"):
            await runtime.submit(boom)

        # Worker still alive and serving.
        assert await runtime.submit(lambda _c: 42) == 42
    finally:
        await runtime.close()


async def test_locked_collection_raises_in_use_error_naming_path() -> None:
    def locked_opener(path: str, /) -> object:
        raise DBError("Anki already open, or media currently syncing.")

    runtime = CollectionRuntime("/tmp/some/collection.anki2", opener=locked_opener)
    with pytest.raises(CollectionInUseError, match="/tmp/some/collection.anki2"):
        await runtime.open()


async def test_missing_collection_file_raises_file_not_found() -> None:
    def missing_opener(path: str, /) -> object:
        raise DBError("database disk image is malformed")

    nonexistent_path = "/tmp/nonexistent/collection.anki2"
    runtime = CollectionRuntime(nonexistent_path, opener=missing_opener)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        await runtime.open()


async def test_submit_before_open_and_after_close_raises() -> None:
    runtime = CollectionRuntime("/x", opener=FakeCollection)
    with pytest.raises(CollectionRuntimeError, match="not open"):
        await runtime.submit(lambda _c: None)

    await runtime.open()
    await runtime.close()
    with pytest.raises(CollectionRuntimeError, match="not open"):
        await runtime.submit(lambda _c: None)


async def test_double_open_raises() -> None:
    runtime = CollectionRuntime("/x", opener=FakeCollection)
    await runtime.open()
    try:
        with pytest.raises(CollectionRuntimeError, match="already opened"):
            await runtime.open()
    finally:
        await runtime.close()


async def test_real_collection_second_open_is_in_use(tmp_path: Path) -> None:
    col_path = str(tmp_path / "collection.anki2")
    first = CollectionRuntime(col_path)
    await first.open()
    try:
        second = CollectionRuntime(col_path)
        with pytest.raises(CollectionInUseError, match=col_path):
            await second.open()
    finally:
        await first.close()

    # Lock released on close: a fresh runtime can reopen.
    third = CollectionRuntime(col_path)
    await third.open()
    await third.close()


async def test_real_collection_roundtrips_a_typed_value(tmp_path: Path) -> None:
    runtime = CollectionRuntime(str(tmp_path / "collection.anki2"))
    await runtime.open()
    try:
        count = await runtime.submit(lambda col: col.note_count())
        assert count == 0
    finally:
        await runtime.close()
