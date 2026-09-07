"""Real Anki API shapes with fake network responses; never contact AnkiWeb."""

import asyncio
import threading
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

import pytest
from anki.errors import NetworkError, SyncError, SyncErrorKind
from anki.sync_pb2 import (
    MediaSyncStatusResponse,
    SyncAuth,
    SyncCollectionResponse,
)

from ankinote.services.anki_credentials import CredentialStore, SyncCredential
from ankinote.services.anki_direct import DirectCollectionClient
from ankinote.services.anki_sync import (
    SyncService,
    SyncState,
    SyncWriteBlocked,
)
from ankinote.services.anki_sync_driver import AnkiSyncDriver
from ankinote.services.collection_runtime import CollectionRuntime


@pytest.fixture
def collection() -> Mock:
    col = Mock()
    col.sync_login.return_value = SyncAuth(hkey="secret-token")
    col.sync_collection.return_value = SyncCollectionResponse()
    col.media_sync_status.side_effect = [
        MediaSyncStatusResponse(active=True),
        MediaSyncStatusResponse(active=False),
    ]
    return col


@pytest.fixture
async def context(tmp_path: Path, collection: Mock):
    path = tmp_path / "collection.anki2"
    path.touch()
    runtime = CollectionRuntime(str(path), opener=lambda _: collection)
    await runtime.open()
    store = CredentialStore(str(path))
    driver = AnkiSyncDriver(runtime, store)
    service = SyncService(driver, interval=10000, retry_initial=100)
    runtime.sync_service = service
    await service.start()
    try:
        yield runtime, store, driver, service
    finally:
        await runtime.close()


async def test_login_private_file_and_wait_for_media(context, collection: Mock, caplog):
    runtime, store, driver, service = context
    state = await driver.login(service, "user@example.com", "secret-password")
    assert state.state == SyncState.IDLE
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert collection.media_sync_status.call_count == 2
    assert collection.sync_collection.call_args.kwargs == {"sync_media": False}
    assert "secret-token" not in repr(store.load())
    assert "secret-token" not in repr(asdict(state)) + caplog.text
    assert "secret-password" not in store.path.read_text() + caplog.text
    await driver.logout(service)
    assert not store.path.exists()
    assert Path(runtime.path).exists()
    calls = collection.sync_collection.call_count
    await service.request()
    assert collection.sync_collection.call_count == calls
    with pytest.raises(ValueError, match="different"):
        await driver.login(service, "other@example.com", "password")


async def test_environment_wins_without_overwriting_saved_secret(context, collection):
    runtime, store, _, service = context
    store.save(SyncCredential("user@example.com", "saved-secret"))
    driver = AnkiSyncDriver(
        runtime, store, username="user@example.com", password="env-pass"
    )
    assert driver.externally_configured
    await driver.sync()
    collection.sync_login.assert_called_once_with(
        "user@example.com", "env-pass", endpoint=None
    )
    assert collection.sync_collection.call_args.args[0].hkey == "secret-token"
    assert store.load().hkey == "saved-secret"
    with pytest.raises(ValueError, match="externally"):
        await driver.login(service, "user@example.com", "password")


@pytest.mark.parametrize("failure", [False, OSError("backup failed")])
async def test_backup_failure_never_performs_full_sync(context, collection, failure):
    _, _, driver, service = context
    collection.sync_collection.return_value = SyncCollectionResponse(
        required=SyncCollectionResponse.FULL_SYNC
    )
    await driver.login(service, "user@example.com", "password")
    if isinstance(failure, Exception):
        collection.create_backup.side_effect = failure
    else:
        collection.create_backup.return_value = failure
    state = await service.resolve_full_sync("download", driver.full_sync)
    assert state.full_sync_required
    collection.full_upload_or_download.assert_not_called()
    collection.close_for_full_sync.assert_not_called()
    with pytest.raises(SyncWriteBlocked):
        async with service.write_scope():
            pytest.fail("writes admitted")


@pytest.mark.parametrize("direction", ["upload", "download"])
async def test_full_sync_backup_reopen_and_media(context, collection, direction):
    _, _, driver, service = context
    collection.sync_collection.return_value = SyncCollectionResponse(
        required=SyncCollectionResponse.FULL_SYNC, server_media_usn=42
    )
    await driver.login(service, "user@example.com", "password")
    assert service.status.full_sync_required
    state = await service.resolve_full_sync(direction, driver.full_sync)
    assert state.state == SyncState.IDLE
    assert not state.full_sync_required
    names = [c[0] for c in collection.mock_calls]
    assert (
        names.index("create_backup")
        < names.index("close_for_full_sync")
        < names.index("full_upload_or_download")
        < names.index("reopen")
        < names.index("sync_media")
    )
    collection.reopen.assert_called_once_with(after_full_sync=True)
    collection.models._clear_cache.assert_called()
    assert collection.full_upload_or_download.call_args.kwargs["upload"] == (
        direction == "upload"
    )


@pytest.mark.parametrize("kind", ["network", "credentials", "other"])
async def test_media_failures_are_separate_and_sanitized(context, collection, kind):
    _, _, driver, service = context
    error = (
        NetworkError("secret-token", None, None, None)
        if kind == "network"
        else (
            SyncError("secret-token", None, None, None, SyncErrorKind.AUTH)
            if kind == "credentials"
            else RuntimeError("secret-token")
        )
    )
    collection.media_sync_status.side_effect = error
    state = await driver.login(service, "user@example.com", "password")
    assert state.result.collection_ok
    assert not state.result.media_ok
    assert state.initialized
    assert "secret-token" not in repr(state)
    assert state.error == ("credentials" if kind == "credentials" else "media")
    assert state.state == (SyncState.PENDING if kind == "network" else SyncState.ERROR)
    async with service.write_scope():
        pass


async def test_cancelled_sync_drains_worker_before_logout(context, collection):
    _, _, driver, service = context
    await driver.login(service, "user@example.com", "password")
    collection.media_sync_status.side_effect = None
    collection.media_sync_status.return_value = MediaSyncStatusResponse()
    entered, release = threading.Event(), threading.Event()

    def sync(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return SyncCollectionResponse()

    collection.sync_collection.side_effect = sync
    sync_task = asyncio.create_task(service.request())
    await asyncio.to_thread(entered.wait, 5)
    logout = asyncio.create_task(driver.logout(service))
    await asyncio.sleep(0.01)
    assert not logout.done()
    release.set()
    await logout
    await asyncio.gather(sync_task, return_exceptions=True)
    assert service.status.state == SyncState.NOT_LOGGED_IN


async def test_logout_during_login_does_not_restore_credentials(context, collection):
    _, store, driver, service = context
    entered, release = threading.Event(), threading.Event()

    def authenticate(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return SyncAuth(hkey="secret-token")

    collection.sync_login.side_effect = authenticate
    login = asyncio.create_task(driver.login(service, "user@example.com", "password"))
    assert await asyncio.to_thread(entered.wait, 5)
    logout = asyncio.create_task(driver.logout(service))
    await asyncio.sleep(0.01)
    release.set()
    await asyncio.gather(login, logout)
    assert not store.path.exists()
    assert service.status.state == SyncState.NOT_LOGGED_IN


async def test_write_batch_excludes_sync_and_coalesces_mutations(context, collection):
    runtime, _, driver, service = context
    await driver.login(service, "user@example.com", "password")
    collection.media_sync_status.side_effect = None
    collection.media_sync_status.return_value = MediaSyncStatusResponse()
    collection.sync_collection.reset_mock()
    async with runtime.write_batch():
        await runtime.submit_write(lambda col: col.write_one())
        pending = asyncio.create_task(service.request())
        await asyncio.sleep(0)
        await runtime.submit_write(lambda col: col.write_two())
        collection.sync_collection.assert_not_called()
    await pending
    collection.sync_collection.assert_called_once()


async def test_real_backup_and_download_cache_invalidation(tmp_path, monkeypatch):
    """Use a real temp collection and replace only the network-facing methods."""
    path = str(tmp_path / "collection.anki2")
    runtime = CollectionRuntime(path)
    await runtime.open()
    try:
        store = CredentialStore(path)
        store.save(SyncCredential("user@example.com", "secret"))
        driver = AnkiSyncDriver(runtime, store)
        client = DirectCollectionClient(runtime)
        assert await client.models.get("Basic") is not None

        def setup(col):
            monkeypatch.setattr(
                col,
                "sync_collection",
                lambda *a, **k: SyncCollectionResponse(
                    required=SyncCollectionResponse.FULL_SYNC
                ),
            )

            def download(**kwargs):
                # Simulate backend replacing the collection while the Python DB is closed.
                model = col.models.by_name("Basic")
                model["name"] = "Downloaded Basic"
                col.models.update(model)

            monkeypatch.setattr(col, "full_upload_or_download", download)
            monkeypatch.setattr(col, "sync_media", lambda auth: None)
            monkeypatch.setattr(
                col, "media_sync_status", lambda: MediaSyncStatusResponse()
            )

        await runtime.submit(setup)
        await driver.full_sync("download")
        assert await client.models.get("Basic") is None
        assert await client.models.get("Downloaded Basic") is not None
        assert list(Path(f"{path}.backups").rglob("*.colpkg"))
    finally:
        await runtime.close()


async def test_failed_download_reopens_and_keeps_writes_blocked(context, collection):
    _, _, driver, service = context
    collection.sync_collection.return_value = SyncCollectionResponse(
        required=SyncCollectionResponse.FULL_SYNC
    )
    await driver.login(service, "user@example.com", "password")
    collection.full_upload_or_download.side_effect = NetworkError(
        "secret-token", None, None, None
    )
    state = await service.resolve_full_sync("download", driver.full_sync)
    assert state.full_sync_required
    collection.reopen.assert_called_once_with(after_full_sync=True)
    collection.sync_media.assert_not_called()
    assert "secret-token" not in repr(state)


@pytest.mark.parametrize(
    ("required", "direction"),
    [
        (SyncCollectionResponse.FULL_DOWNLOAD, "upload"),
        (SyncCollectionResponse.FULL_UPLOAD, "download"),
    ],
)
async def test_unavailable_direction_never_performs_full_sync(
    context, collection, required, direction
):
    _, _, driver, service = context
    collection.sync_collection.return_value = SyncCollectionResponse(required=required)
    await driver.login(service, "user@example.com", "password")
    state = await service.resolve_full_sync(direction, driver.full_sync)
    assert state.state == SyncState.NEEDS_FULL_SYNC_CHOICE
    collection.create_backup.assert_not_called()
    collection.full_upload_or_download.assert_not_called()
