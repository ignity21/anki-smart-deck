"""In-process Anki collection backend (``ANKI_BACKEND=collection``).

Implements the same narrow client contract as :class:`AnkiConnectClient`, but
against a local Anki collection driven through :class:`CollectionRuntime`. Every
method hands a small callable to the runtime worker; raw Anki objects (model and
note dicts, ``Note`` instances) never leave that thread — only plain values and
ankinote's own dataclasses cross back.
"""

from __future__ import annotations

from typing import Any

from ankinote.services.anki import (
    AnkiDeckService,
    AnkiMediaService,
    AnkiModelService,
    AnkiNoteService,
    ModelAlreadyExists,
    ModelField,
    ModelNotFound,
    ModelTemplate,
    NoteModel,
    TemplateUpsert,
)
from ankinote.services.collection_runtime import CollectionRuntime


def _escape_search(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("*", "\\*")
        .replace("_", "\\_")
    )


def _build_note_query(
    deck_name: str, unique_fields: dict[str, str], model_name: str | None
) -> str:
    parts = [f'deck:"{_escape_search(deck_name)}"']
    if model_name is not None:
        parts.append(f'note:"{_escape_search(model_name)}"')
    for field_name, value in unique_fields.items():
        parts.append(f'{field_name}:"{_escape_search(value)}"')
    return " ".join(parts)


def _model_to_notemodel(model: dict[str, Any]) -> NoteModel:
    fields = [
        ModelField(
            id=fld.get("id") or 0,
            name=fld["name"],
            description=fld.get("description", ""),
            order=fld.get("ord"),
            font=fld.get("font", "Arial"),
            size=fld.get("size", 20),
            plain_text=fld.get("plainText", False),
            collapsed=fld.get("collapsed", True),
            exclude_from_search=fld.get("excludeFromSearch", False),
        )
        for fld in model["flds"]
    ]
    templates = [
        ModelTemplate(
            id=tmpl.get("id"),
            name=tmpl["name"],
            question_format=tmpl["qfmt"],
            answer_format=tmpl["afmt"],
            order=tmpl.get("ord"),
        )
        for tmpl in model["tmpls"]
    ]
    return NoteModel(
        id=model["id"],
        name=model["name"],
        type=model.get("type", 0),
        sort_field=model.get("sortf", 0),
        deck_id=model.get("did"),
        templates=templates,
        fields=fields,
        css=model.get("css", ""),
        latex_pre=model.get("latexPre", ""),
        latex_post=model.get("latexPost", ""),
        latex_svg=model.get("latexsvg", False),
        requirements=model.get("req", []),
    )


class _DirectModelService(AnkiModelService):
    def __init__(self, runtime: CollectionRuntime) -> None:
        self._runtime = runtime

    async def exists(self, model_name: str) -> bool:
        return await self._runtime.submit(
            lambda col: col.models.by_name(model_name) is not None
        )

    async def get(self, model_name: str) -> NoteModel | None:
        return await self._runtime.submit(lambda col: self._get(col, model_name))

    @staticmethod
    def _get(col: Any, model_name: str) -> NoteModel | None:
        model = col.models.by_name(model_name)
        return _model_to_notemodel(model) if model is not None else None

    async def create(
        self,
        model_name: str,
        fields: list[str],
        templates: list[dict[str, str]],
        css: str = "",
        is_cloze: bool = False,
    ) -> NoteModel:
        return await self._runtime.submit(
            lambda col: self._create(col, model_name, fields, templates, css, is_cloze)
        )

    @staticmethod
    def _create(
        col: Any,
        model_name: str,
        fields: list[str],
        templates: list[dict[str, str]],
        css: str,
        is_cloze: bool,
    ) -> NoteModel:
        from anki.consts import MODEL_CLOZE, MODEL_STD

        mm = col.models
        if mm.by_name(model_name) is not None:
            raise ModelAlreadyExists(f"Model '{model_name}' already exists")

        model = mm.new(model_name)
        model["type"] = MODEL_CLOZE if is_cloze else MODEL_STD
        for field_name in fields:
            mm.add_field(model, mm.new_field(field_name))
        for template in templates:
            tmpl = mm.new_template(template["Name"])
            tmpl["qfmt"] = template["Front"]
            tmpl["afmt"] = template["Back"]
            mm.add_template(model, tmpl)
        if css:
            model["css"] = css
        mm.add_dict(model)
        return _model_to_notemodel(mm.by_name(model_name))

    async def update_templates(
        self, model_name: str, templates: list[TemplateUpsert]
    ) -> None:
        await self._runtime.submit(
            lambda col: self._update_templates(col, model_name, templates)
        )

    @staticmethod
    def _update_templates(
        col: Any, model_name: str, templates: list[TemplateUpsert]
    ) -> None:
        mm = col.models
        model = mm.by_name(model_name)
        if model is None:
            raise ModelNotFound(f"Model '{model_name}' not found")

        for upsert in templates:
            by_name = {tmpl["name"]: tmpl for tmpl in model["tmpls"]}
            match_name = upsert.previous_name or upsert.name

            if match_name not in by_name:
                tmpl = mm.new_template(upsert.name)
                tmpl["qfmt"] = upsert.question_format
                tmpl["afmt"] = upsert.answer_format
                mm.add_template(model, tmpl)
                continue

            tmpl = by_name[match_name]
            if upsert.previous_name is not None and upsert.name != upsert.previous_name:
                tmpl["name"] = upsert.name
            tmpl["qfmt"] = upsert.question_format
            tmpl["afmt"] = upsert.answer_format

        mm.update_dict(model)

    async def update_styling(self, model_name: str, css: str) -> None:
        await self._runtime.submit(
            lambda col: self._update_styling(col, model_name, css)
        )

    @staticmethod
    def _update_styling(col: Any, model_name: str, css: str) -> None:
        mm = col.models
        model = mm.by_name(model_name)
        if model is None:
            raise ModelNotFound(f"Model '{model_name}' not found")
        model["css"] = css
        mm.update_dict(model)

    async def add_field(self, model_name: str, field_name: str) -> None:
        await self._runtime.submit(
            lambda col: self._add_field(col, model_name, field_name)
        )

    @staticmethod
    def _add_field(col: Any, model_name: str, field_name: str) -> None:
        mm = col.models
        model = mm.by_name(model_name)
        if model is None:
            raise ModelNotFound(f"Model '{model_name}' not found")
        if any(fld["name"] == field_name for fld in model["flds"]):
            return
        mm.add_field(model, mm.new_field(field_name))
        mm.update_dict(model)

    async def ensure_fields(self, model_name: str, field_names: list[str]) -> None:
        await self._runtime.submit(
            lambda col: self._ensure_fields(col, model_name, field_names)
        )

    @staticmethod
    def _ensure_fields(col: Any, model_name: str, field_names: list[str]) -> None:
        mm = col.models
        model = mm.by_name(model_name)
        if model is None:
            return
        existing = {fld["name"] for fld in model["flds"]}
        added = False
        for field_name in field_names:
            if field_name not in existing:
                mm.add_field(model, mm.new_field(field_name))
                added = True
        if added:
            mm.update_dict(model)


class _DirectDeckService(AnkiDeckService):
    def __init__(self, runtime: CollectionRuntime) -> None:
        self._runtime = runtime

    async def create(self, deck_name: str) -> int:
        return await self._runtime.submit(lambda col: col.decks.id(deck_name))

    async def exists(self, deck_name: str) -> bool:
        return await self._runtime.submit(
            lambda col: col.decks.by_name(deck_name) is not None
        )


class _DirectNoteService(AnkiNoteService):
    def __init__(self, runtime: CollectionRuntime) -> None:
        self._runtime = runtime

    async def find(
        self,
        deck_name: str,
        unique_fields: dict[str, str],
        *,
        model_name: str | None = None,
    ) -> int | None:
        query = _build_note_query(deck_name, unique_fields, model_name)
        note_ids = await self._runtime.submit(lambda col: list(col.find_notes(query)))
        if not note_ids:
            return None
        if len(note_ids) > 1:
            raise KeyError(
                f"Expected exactly one note matching {unique_fields} in deck "
                f"'{deck_name}', but found {len(note_ids)}"
            )
        return note_ids[0]

    async def add(
        self,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
        allow_duplicate: bool = False,
    ) -> int:
        return await self._runtime.submit(
            lambda col: self._add(col, deck_name, model_name, fields, tags)
        )

    @staticmethod
    def _add(
        col: Any,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str] | None,
    ) -> int:
        model = col.models.by_name(model_name)
        if model is None:
            raise ModelNotFound(f"Model '{model_name}' not found")
        deck_id = col.decks.id(deck_name)
        note = col.new_note(model)
        for field_name, value in fields.items():
            note[field_name] = value
        if tags:
            note.tags = list(tags)
        col.add_note(note, deck_id)
        return note.id

    async def update_fields(self, note_id: int, fields: dict[str, str]) -> None:
        await self._runtime.submit(
            lambda col: self._update_fields(col, note_id, fields)
        )

    @staticmethod
    def _update_fields(col: Any, note_id: int, fields: dict[str, str]) -> None:
        note = col.get_note(note_id)
        for field_name, value in fields.items():
            note[field_name] = value
        col.update_note(note)

    async def update_tags(self, note_id: int, tags: list[str]) -> None:
        await self._runtime.submit(lambda col: self._update_tags(col, note_id, tags))

    @staticmethod
    def _update_tags(col: Any, note_id: int, tags: list[str]) -> None:
        note = col.get_note(note_id)
        note.tags = list(tags)
        col.update_note(note)


class _DirectMediaService(AnkiMediaService):
    def __init__(self, runtime: CollectionRuntime) -> None:
        self._runtime = runtime

    async def store_file(self, filename: str, data: bytes) -> str:
        return await self._runtime.submit(
            lambda col: col.media.write_data(filename, data)
        )


class DirectCollectionClient:
    """Collection client backed by a local Anki collection."""

    def __init__(self, runtime: CollectionRuntime) -> None:
        self._runtime = runtime
        self._models = _DirectModelService(runtime)
        self._decks = _DirectDeckService(runtime)
        self._notes = _DirectNoteService(runtime)
        self._media = _DirectMediaService(runtime)

    @property
    def models(self) -> AnkiModelService:
        return self._models

    @property
    def decks(self) -> AnkiDeckService:
        return self._decks

    @property
    def notes(self) -> AnkiNoteService:
        return self._notes

    @property
    def media(self) -> AnkiMediaService:
        return self._media
