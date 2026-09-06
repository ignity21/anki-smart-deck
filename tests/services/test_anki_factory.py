"""Tests for the Anki backend selection factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from ankinote.services.anki import AnkiConnectClient
from ankinote.services.anki_factory import AnkiBackendConfigError, create_anki_client

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "ankinote"
_FACTORY_MODULE = _SRC_ROOT / "services" / "anki_factory.py"
_DEFINING_MODULE = _SRC_ROOT / "services" / "anki.py"


class TestBackendSelection:
    def test_defaults_to_ankiconnect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("ankinote.config.envs.ANKI_BACKEND", "connect")
        assert isinstance(create_anki_client(), AnkiConnectClient)

    def test_blank_backend_defaults_to_ankiconnect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ankinote.config.envs.ANKI_BACKEND", "")
        assert isinstance(create_anki_client(), AnkiConnectClient)

    def test_unknown_backend_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("ankinote.config.envs.ANKI_BACKEND", "nonsense")
        with pytest.raises(AnkiBackendConfigError, match="Unknown ANKI_BACKEND"):
            create_anki_client()

    def test_collection_backend_requires_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ankinote.config.envs.ANKI_BACKEND", "collection")
        monkeypatch.setattr("ankinote.config.envs.ANKI_COLLECTION_PATH", "")
        with pytest.raises(AnkiBackendConfigError, match="ANKI_COLLECTION_PATH"):
            create_anki_client()

    def test_collection_backend_not_implemented_yet(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ankinote.config.envs.ANKI_BACKEND", "collection")
        monkeypatch.setattr(
            "ankinote.config.envs.ANKI_COLLECTION_PATH", "/tmp/collection"
        )
        with pytest.raises(AnkiBackendConfigError, match="not implemented"):
            create_anki_client()


def test_no_direct_backend_construction_outside_factory() -> None:
    """Only the factory (and the module that defines it) may name the concrete
    ``AnkiConnectClient`` backend; every other module goes through the factory."""
    offenders: list[str] = []
    for path in _SRC_ROOT.rglob("*.py"):
        if path in (_FACTORY_MODULE, _DEFINING_MODULE):
            continue
        if "AnkiConnectClient" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(_SRC_ROOT)))
    assert not offenders, (
        f"modules reference AnkiConnectClient directly instead of "
        f"create_anki_client(): {offenders}"
    )
