"""Exercise scheduling and collection write policy without AnkiWeb access."""

import asyncio
import threading
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from ankinote.services.anki_direct import DirectCollectionClient
from ankinote.services.anki_sync import (
    FullSyncRequired,
    SyncCredentialError,
    SyncNetworkError,
    SyncResult,
    SyncService,
    SyncSnapshot,
    SyncState,
    SyncStateStore,
    SyncWriteBlocked,
)
from ankinote.services.collection_runtime import CollectionRuntime


class FakeDriver:
    def __init__(self, *outcomes: SyncResult | Exception) -> None:
        self.outcomes = deque(outcomes)
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()

    async def sync(self) -> SyncResult:
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        outcome = self.outcomes.popleft() if self.outcomes else SyncResult()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClock:
    def __init__(self) -> None:
        self.waiters: asyncio.Queue[tuple[float, asyncio.Event]] = asyncio.Queue()

    async def sleep(self, delay: float) -> None:
        event = asyncio.Event()
        self.waiters.put_nowait((delay, event))
        await event.wait()

    async def next(self, expected: float) -> asyncio.Event:
        async with asyncio.timeout(2):
            delay, event = await self.waiters.get()
        assert delay == expected
        return event


async def test_manual_sync_skips_backoff_and_shares_attempt(services):
    driver = FakeDriver(SyncNetworkError())
    service = services(driver, retry_initial=100)
    await service.start(authenticated=True)
    assert service.status.state == SyncState.PENDING
    await asyncio.gather(service.sync_now(), service.sync_now())
    assert driver.calls == 2
    assert service.status.state == SyncState.IDLE


async def test_interval_persists_and_restarts_timer(services, tmp_path):
    clock = FakeClock()
    store = SyncStateStore(tmp_path / "sync.json")
    service = services(FakeDriver(), sleep=clock.sleep, save=store.save)
    await service.start()
    await clock.next(300)
    service.set_interval(120)
    await clock.next(120)
    assert store.load().interval_seconds == 120
    restored = services(FakeDriver(), snapshot=store.load())
    assert restored.status.interval_seconds == 120
    for value in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            service.set_interval(value)
    assert service.status.interval_seconds == 120


async def test_reauthentication_clears_error_but_keeps_full_sync_choice(services):
    service = services(
        FakeDriver(),
        snapshot=SyncSnapshot(
            state=SyncState.ERROR,
            initialized=True,
            full_sync_required=True,
            error="credentials",
        ),
    )
    await service.start(authenticated=True)
    await service.reauthenticate()
    assert service.status.error is None
    assert service.status.full_sync_required
    assert service.write_blocked


@pytest.fixture
async def services() -> AsyncIterator[Callable[..., SyncService]]:
    owned: list[SyncService] = []

    def create(driver: FakeDriver, **kwargs: object) -> SyncService:
        service = SyncService(driver, **kwargs)
        owned.append(service)
        return service

    yield create
    for service in owned:
        await service.close()


async def test_login_initialization_and_subsequent_sync(services) -> None:
    snapshots: list[SyncSnapshot] = []
    driver = FakeDriver()
    service = services(driver, save=snapshots.append)
    assert (await service.start()).state == SyncState.NOT_LOGGED_IN
    assert driver.calls == 0
    with pytest.raises(SyncWriteBlocked):
        async with service.write_scope():
            pytest.fail("Uninitialized writes must be blocked")
    assert (await service.reauthenticate()).state == SyncState.IDLE
    first_success = service.status.last_success
    assert first_success is not None
    assert SyncState.INITIALIZING in [item.state for item in snapshots]
    assert (await service.request()).state == SyncState.IDLE
    assert SyncState.SYNCING in [item.state for item in snapshots]
    assert service.status.last_success >= first_success


async def test_three_overlapping_requests_share_one_attempt(services) -> None:
    driver = FakeDriver()
    service = services(driver)
    await service.start()
    driver.release.clear()
    first = asyncio.create_task(service.reauthenticate())
    await driver.entered.wait()
    async with asyncio.TaskGroup() as group:
        second = group.create_task(service.request())
        third = group.create_task(service.request())
        await asyncio.sleep(0)
        driver.release.set()
    assert await first == second.result() == third.result()
    assert driver.calls == 1


async def test_cancelling_waiter_does_not_cancel_shared_sync(services) -> None:
    driver = FakeDriver()
    service = services(driver)
    await service.start()
    driver.release.clear()
    waiter = asyncio.create_task(service.reauthenticate())
    await driver.entered.wait()
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    driver.release.set()
    assert (await service.request()).state == SyncState.IDLE
    assert driver.calls == 1


async def test_network_backoff_is_capped_and_timer_cannot_bypass_it(services) -> None:
    clock = FakeClock()
    driver = FakeDriver(*[SyncNetworkError("secret") for _ in range(3)])
    service = services(driver, sleep=clock.sleep, retry_initial=2, retry_max=4)
    assert (await service.start(authenticated=True)).state == SyncState.PENDING
    timer = await clock.next(300)
    for delay in (2, 4, 4):
        retry = await clock.next(delay)
        calls = driver.calls
        timer.set()
        timer = await clock.next(300)
        await service.request()
        assert driver.calls == calls
        driver.entered.clear()
        retry.set()
        await driver.entered.wait()
    assert service.status.state == SyncState.IDLE
    assert driver.calls == 4
    assert service.status.error is None


async def test_credential_failure_stops_timer_and_manual_retries(services) -> None:
    clock = FakeClock()
    driver = FakeDriver(SyncCredentialError("do not expose password"))
    service = services(driver, sleep=clock.sleep)
    status = await service.start(authenticated=True)
    assert status.state == SyncState.ERROR
    assert status.error == "credentials"
    timer = await clock.next(300)
    timer.set()
    await clock.next(300)
    await service.request()
    assert driver.calls == 1
    assert (await service.reauthenticate()).state == SyncState.IDLE
    assert driver.calls == 2


async def test_timer_syncs_every_five_minutes_and_logout_pauses_it(services) -> None:
    clock = FakeClock()
    driver = FakeDriver()
    service = services(driver, sleep=clock.sleep)
    await service.start(authenticated=True)
    timer = await clock.next(300)
    timer.set()
    timer = await clock.next(300)
    assert driver.calls == 2
    await service.logout()
    timer.set()
    await clock.next(300)
    assert driver.calls == 2
    assert service.status.state == SyncState.NOT_LOGGED_IN


@pytest.mark.parametrize("initialized", [False, True])
async def test_offline_writes_only_after_initialization(services, initialized) -> None:
    service = services(
        FakeDriver(SyncNetworkError()),
        snapshot=SyncSnapshot(initialized=initialized),
    )
    await service.start(authenticated=True)
    assert service.status.state == SyncState.PENDING
    if initialized:
        async with service.write_scope():
            pass
    else:
        with pytest.raises(SyncWriteBlocked):
            async with service.write_scope():
                pytest.fail("Initial sync remains unresolved")


async def test_full_sync_choice_survives_logout_and_restart(services, tmp_path) -> None:
    store = SyncStateStore(tmp_path / "sync-state.json")
    service = services(
        FakeDriver(FullSyncRequired()),
        snapshot=SyncSnapshot(initialized=True),
        save=store.save,
    )
    await service.start(authenticated=True)
    assert service.status.state == SyncState.NEEDS_FULL_SYNC_CHOICE
    await service.logout()
    restored = services(FakeDriver(), snapshot=store.load())
    await restored.start(authenticated=True)
    assert restored.status.state == SyncState.NEEDS_FULL_SYNC_CHOICE
    with pytest.raises(SyncWriteBlocked):
        async with restored.write_scope():
            pytest.fail("Logout/restart must not discard the conflict")


async def test_credential_failure_remains_paused_after_restart(services) -> None:
    service = services(FakeDriver(SyncCredentialError()))
    await service.start(authenticated=True)
    driver = FakeDriver()
    restored = services(driver, snapshot=service.status)
    await restored.start(authenticated=True)
    await restored.request()
    assert driver.calls == 0
    await restored.reauthenticate()
    assert driver.calls == 1


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        (SyncResult(media_ok=False), "media"),
        (SyncResult(collection_ok=False, media_ok=False), "collection"),
        (RuntimeError("credential secret"), "driver"),
    ],
)
async def test_failures_preserve_last_success(services, outcome, error) -> None:
    driver = FakeDriver(SyncResult(), outcome)
    service = services(driver)
    await service.start(authenticated=True)
    previous = service.status.last_success
    status = await service.request()
    assert status.state == SyncState.ERROR
    assert status.error == error
    assert status.last_success == previous
    assert status.initialized
    if isinstance(outcome, SyncResult):
        assert status.result == outcome


async def test_sync_waits_for_admitted_write_and_status_stays_available(
    services,
) -> None:
    driver = FakeDriver()
    service = services(driver)
    await service.start(authenticated=True)
    async with service.write_scope():
        request = asyncio.create_task(service.request())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert driver.calls == 1
        assert service.status.initialized
    await request
    assert driver.calls == 2


async def test_write_waiting_for_sync_rechecks_full_sync_choice(services) -> None:
    driver = FakeDriver(SyncResult(), FullSyncRequired())
    service = services(driver)
    await service.start(authenticated=True)
    driver.release.clear()
    driver.entered.clear()
    request = asyncio.create_task(service.request())
    await driver.entered.wait()

    async def write() -> None:
        async with service.write_scope():
            pytest.fail("Queued write must recheck the new conflict")

    mutation = asyncio.create_task(write())
    await asyncio.sleep(0)
    driver.release.set()
    await request
    with pytest.raises(SyncWriteBlocked):
        await mutation


async def test_close_cancels_active_sync_and_is_idempotent(services) -> None:
    driver = FakeDriver()
    service = services(driver)
    await service.start()
    driver.release.clear()
    request = asyncio.create_task(service.reauthenticate())
    await driver.entered.wait()
    await service.close()
    with pytest.raises(asyncio.CancelledError):
        await request
    assert service.status.state == SyncState.PENDING
    await service.close()
    with pytest.raises(RuntimeError, match="not running"):
        await service.request()


async def test_close_cancels_scheduled_retry(services) -> None:
    clock = FakeClock()
    driver = FakeDriver(SyncNetworkError())
    service = services(driver, sleep=clock.sleep)
    await service.start(authenticated=True)
    timer = await clock.next(300)
    retry = await clock.next(1)
    await service.close()
    timer.set()
    retry.set()
    await asyncio.sleep(0)
    assert driver.calls == 1


async def test_direct_backend_blocks_all_mutations_but_allows_reads(services) -> None:
    service = services(
        FakeDriver(FullSyncRequired()), snapshot=SyncSnapshot(initialized=True)
    )
    await service.start(authenticated=True)
    collection = Mock()
    collection.models.by_name.return_value = None
    collection.decks.by_name.return_value = None
    collection.find_notes.return_value = []
    runtime = CollectionRuntime(
        "unused", opener=lambda _: collection, sync_service=service
    )
    await runtime.open()
    client = DirectCollectionClient(runtime)
    try:
        mutations = [
            lambda: client.models.create("T", ["Front"], []),
            lambda: client.models.update_templates("T", []),
            lambda: client.models.update_styling("T", "css"),
            lambda: client.models.add_field("T", "Extra"),
            lambda: client.models.ensure_fields("T", ["Extra"]),
            lambda: client.decks.create("D"),
            lambda: client.notes.add("D", "T", {"Front": "test"}),
            lambda: client.notes.update_fields(1, {"Front": "test"}),
            lambda: client.notes.update_tags(1, ["test"]),
            lambda: client.media.store_file("a.mp3", b"audio"),
        ]
        for mutate in mutations:
            with pytest.raises(SyncWriteBlocked):
                await mutate()
        assert collection.mock_calls == []
        assert not await client.models.exists("T")
        assert await client.models.get("T") is None
        assert not await client.decks.exists("D")
        assert await client.notes.find("D", {"Front": "test"}) is None
    finally:
        await runtime.close()


def test_state_store_round_trip_and_invalid_data(tmp_path: Path) -> None:
    path = tmp_path / "sync.json"
    store = SyncStateStore(path)
    assert store.load() == SyncSnapshot()
    snapshot = SyncSnapshot(
        state=SyncState.PENDING,
        initialized=True,
        last_success=datetime.now(UTC),
        result=SyncResult(media_ok=False),
    )
    store.save(snapshot)
    assert store.load() == snapshot
    store.save(replace(snapshot, full_sync_required=True))
    assert store.load().full_sync_required
    path.write_text("broken")
    with pytest.raises(ValueError):
        store.load()


def test_failed_state_replacement_preserves_previous_file(
    tmp_path, monkeypatch
) -> None:
    store = SyncStateStore(tmp_path / "sync.json")
    previous = SyncSnapshot(initialized=True)
    store.save(previous)
    monkeypatch.setattr(Path, "replace", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        store.save(replace(previous, full_sync_required=True))
    assert store.load() == previous
    assert list(tmp_path.iterdir()) == [tmp_path / "sync.json"]


async def test_persistence_failure_blocks_writes(services) -> None:
    service = services(
        FakeDriver(),
        snapshot=SyncSnapshot(initialized=True),
        save=Mock(side_effect=OSError("disk full")),
    )
    with pytest.raises(OSError):
        await service.start(authenticated=True)
    assert service.status.error == "state_store"
    with pytest.raises(SyncWriteBlocked):
        async with service.write_scope():
            pytest.fail("Failed state persistence must block writes")


async def test_direct_backend_permits_offline_write_after_setup(services) -> None:
    service = services(
        FakeDriver(SyncNetworkError()), snapshot=SyncSnapshot(initialized=True)
    )
    await service.start(authenticated=True)
    collection = Mock()
    collection.decks.id.return_value = 42
    runtime = CollectionRuntime(
        "unused", opener=lambda _: collection, sync_service=service
    )
    await runtime.open()
    try:
        assert await DirectCollectionClient(runtime).decks.create("D") == 42
        collection.decks.id.assert_called_once_with("D")
    finally:
        await runtime.close()


async def test_cancelled_worker_write_finishes_before_sync(services) -> None:
    driver = FakeDriver()
    service = services(driver)
    await service.start(authenticated=True)
    runtime = CollectionRuntime("unused", opener=lambda _: Mock(), sync_service=service)
    await runtime.open()
    entered = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()

    def write(_: object) -> None:
        loop.call_soon_threadsafe(entered.set)
        assert release.wait(5)

    mutation = asyncio.create_task(runtime.submit_write(write))
    try:
        await entered.wait()
        mutation.cancel()
        request = asyncio.create_task(service.request())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert driver.calls == 1
        assert not mutation.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await mutation
        await request
        assert driver.calls == 2
    finally:
        release.set()
        await runtime.close()
