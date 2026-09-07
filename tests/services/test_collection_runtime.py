"""Tests for the single-threaded Anki collection runtime."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from ankinote.services.collection_runtime import (
    CollectionInUseError,
    CollectionOpenError,
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


async def test_locked_collection_raises_in_use_error_naming_path(
    tmp_path: Path,
) -> None:
    col = tmp_path / "collection.anki2"
    col.touch()

    def locked_opener(path: str, /) -> object:
        raise DBError("Anki already open, or media currently syncing.")

    runtime = CollectionRuntime(str(col), opener=locked_opener)
    with pytest.raises(CollectionInUseError, match=str(col)):
        await runtime.open()


async def test_missing_collection_directory_raises_file_not_found(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "nope" / "collection.anki2"
    runtime = CollectionRuntime(str(missing))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        await runtime.open()


async def test_collection_path_that_is_a_directory_raises_open_error(
    tmp_path: Path,
) -> None:
    as_dir = tmp_path / "collection.anki2"
    as_dir.mkdir()
    runtime = CollectionRuntime(str(as_dir))
    with pytest.raises(CollectionOpenError, match="is a directory"):
        await runtime.open()


async def test_corrupt_collection_file_raises_open_error(tmp_path: Path) -> None:
    junk = tmp_path / "collection.anki2"
    junk.write_bytes(b"this is not an sqlite database" * 8)
    runtime = CollectionRuntime(str(junk))
    with pytest.raises(CollectionOpenError, match="not a valid Anki collection"):
        await runtime.open()


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory permissions")
async def test_unwritable_collection_directory_raises_open_error(
    tmp_path: Path,
) -> None:
    locked_dir = tmp_path / "ro"
    locked_dir.mkdir()
    col = locked_dir / "collection.anki2"
    locked_dir.chmod(0o500)
    try:
        runtime = CollectionRuntime(str(col))
        with pytest.raises(CollectionOpenError, match="not.*writable"):
            await runtime.open()
    finally:
        locked_dir.chmod(0o700)


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
