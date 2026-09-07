"""Account commands use safe output and explicit sync admission."""

import importlib
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from ankinote.cli.main import cli
from ankinote.services.anki_sync import (
    FullSyncRequired,
    SyncResult,
    SyncService,
    SyncSnapshot,
    SyncState,
)

commands = importlib.import_module("ankinote.cli.anki")


@pytest.fixture
def backend(monkeypatch):
    driver = SimpleNamespace(
        account="learner@example.com",
        externally_configured=False,
        sync=AsyncMock(return_value=SyncResult()),
        full_sync=AsyncMock(return_value=SyncResult()),
    )
    config = SimpleNamespace(
        snapshot=SyncSnapshot(state=SyncState.IDLE, initialized=True), runtime=None
    )

    async def login(service, email, password):
        return await service.reauthenticate()

    async def logout(service):
        await service.logout()

    driver.login = AsyncMock(side_effect=login)
    driver.logout = AsyncMock(side_effect=logout)

    @asynccontextmanager
    async def scope(*, synchronize=True):
        assert not synchronize
        service = SyncService(driver, snapshot=config.snapshot)
        await service.start(authenticated=True, synchronize=False)
        config.runtime = SimpleNamespace(sync_service=service, sync_driver=driver)
        try:
            yield
        finally:
            await service.close()

    monkeypatch.setattr(commands, "anki_backend_scope", scope)
    monkeypatch.setattr(commands, "get_shared_runtime", lambda: config.runtime)
    return config, driver


@pytest.mark.parametrize("conflict", [False, True])
def test_status_exit_code_and_no_network(backend, conflict):
    config, driver = backend
    config.snapshot = SyncSnapshot(
        state=SyncState.IDLE, initialized=True, full_sync_required=conflict
    )
    result = CliRunner().invoke(cli, ["anki", "status"])
    assert result.exit_code == int(conflict), result.output
    assert json.loads(result.output)["full_sync_required"] == conflict
    driver.sync.assert_not_awaited()


def test_explicit_direction_resolves_full_sync(backend):
    _, driver = backend
    driver.sync.side_effect = FullSyncRequired()
    result = CliRunner().invoke(cli, ["anki", "sync", "--direction", "upload"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["state"] == "idle"
    driver.full_sync.assert_awaited_once_with("upload")


def test_full_sync_without_direction_returns_nonzero(backend):
    _, driver = backend
    driver.sync.side_effect = FullSyncRequired()
    result = CliRunner().invoke(cli, ["anki", "sync"])
    assert result.exit_code == 1
    driver.full_sync.assert_not_awaited()


def test_login_password_not_echoed(backend):
    _, driver = backend
    result = CliRunner().invoke(
        cli,
        ["anki", "login", "--email", "learner@example.com"],
        input="private-password\n",
    )
    assert result.exit_code == 0, result.output
    assert "private-password" not in result.output
    assert driver.login.await_args.args[1:] == (
        "learner@example.com",
        "private-password",
    )


def test_logout_has_no_network_sync(backend):
    _, driver = backend
    result = CliRunner().invoke(cli, ["anki", "logout"])
    assert result.exit_code == 0, result.output
    driver.logout.assert_awaited_once()
    driver.sync.assert_not_awaited()


def test_exception_output_is_sanitized(backend):
    _, driver = backend
    driver.logout.side_effect = RuntimeError("private-token")
    result = CliRunner().invoke(cli, ["anki", "logout"])
    assert result.exit_code != 0
    assert "private-token" not in result.output
