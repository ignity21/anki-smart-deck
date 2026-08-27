"""Tests for the GUI note-type synchronisation wiring."""

from typing import cast

import pytest

from ankinote.services.anki import AnkiCollectionClient
from ankinote.ui.pages import notetypes


@pytest.mark.asyncio
async def test_sentence_note_type_sync_uses_only_sentence_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentence sync does not pass WordCollection's image dependency."""
    captured_kwargs: dict[str, object] = {}

    class FakeSentenceCollection:
        def __init__(self, client: AnkiCollectionClient, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

        async def ensure_in_anki(self) -> None:
            return None

    monkeypatch.setattr(notetypes, "SentenceCollection", FakeSentenceCollection)
    spec = next(spec for spec in notetypes._build_specs() if spec.key == "sentence")

    await spec.sync(cast(AnkiCollectionClient, object()))

    assert "image_service" not in captured_kwargs
    assert captured_kwargs["notetype_name"] == "AINote Sentence V2"
    assert captured_kwargs["deck_name"] == "AINote::Sentences"
