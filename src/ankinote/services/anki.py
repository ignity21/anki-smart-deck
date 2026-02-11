import base64
from dataclasses import dataclass, field
from typing import Any

from ankinote.utils.httpcli import get_session


class ModelAlreadyExists(Exception):
    """Raised when attempting to create a model that already exists."""

    pass


class ModelNotFound(Exception):
    """Raised when a specified model is not found."""

    pass


@dataclass
class ModelField:
    """Represents a field in an Anki note model."""

    id: int
    name: str
    description: str = field(default="")
    order: int | None = field(doc="Display order in the note type", default=None)
    font: str = field(default="Arial")
    size: int = field(doc="Font size in points", default=20)
    plain_text: bool = field(
        doc="Whether to store as plain text without formatting", default=False
    )
    collapsed: bool = field(
        doc="Whether the field is collapsed in the editor", default=True
    )
    exclude_from_search: bool = field(default=False)


@dataclass
class ModelTemplate:
    """Represents a card template in an Anki note model."""

    name: str
    question_format: str = field(doc="HTML/template for the question side")
    answer_format: str = field(doc="HTML/template for the answer side")
    id: int | None = field(doc="Template ID (assigned by Anki)", default=None)
    order: int | None = field(doc="Display order of this template", default=None)


@dataclass
class NoteModel:
    """Represents an Anki note model (note type)."""

    id: int
    name: str
    type: int = field(doc="Model type (0 for standard)", default=0)
    sort_field: int = field(doc="Index of the field used for sorting", default=0)
    deck_id: int | None = field(
        doc="Optional default deck for this note type", default=None
    )
    templates: list[ModelTemplate] = field(default_factory=list, repr=False)
    fields: list[ModelField] = field(default_factory=list)
    css: str = field(doc="CSS styling for cards", default="", repr=False)
    latex_pre: str = field(doc="LaTeX preamble", default="")
    latex_post: str = field(doc="LaTeX postamble", default="")
    latex_svg: bool = field(doc="Whether to render LaTeX as SVG", default=False)
    requirements: list[list[Any]] = field(
        doc="Card generation requirements", default_factory=list
    )


class ModelClient:
    """Client for managing Anki note models."""

    def __init__(self, client: "AnkiConnectClient") -> None:
        """Initialize ModelClient.

        Args:
            client: The parent AnkiConnectClient instance
        """
        self._client = client

    async def list(self) -> list[str]:
        """List all note types (models) in Anki.

        Returns:
            List of note type names
        """
        return await self._client._invoke("modelNames")

    async def exists(self, model_name: str) -> bool:
        try:
            models = await self._client._invoke(
                "findModelsByName",
                params={
                    "modelNames": [
                        model_name,
                    ]
                },
            )
            assert len(models) == 1
            return True
        except RuntimeError:
            return False

    async def info(self, model_name: str) -> NoteModel:
        """get details of a note type (model) by name.

        Args:
            model_name: The note type name

        Returns:
            NoteModel instance

        Raises:
            KeyError: If model not found
        """
        try:
            model_list = await self._client._invoke(
                "findModelsByName",
                params={
                    "modelNames": [
                        model_name,
                    ]
                },
            )
        except RuntimeError:
            raise KeyError(f"Model '{model_name}' not found")

        model_dict = model_list[0]
        return self._model_dict_to_notemodel(model_dict)

    def _model_dict_to_notemodel(self, model_dict: dict[str, Any]) -> NoteModel:
        """Convert a model dictionary from AnkiConnect to a NoteModel instance."""
        # Convert field dictionaries to Field objects
        fields = [
            ModelField(
                id=fld["id"],
                name=fld["name"],
                description=fld["description"],
                order=fld["ord"],
                font=fld["font"],
                size=fld["size"],
                plain_text=fld["plainText"],
                collapsed=fld["collapsed"],
                exclude_from_search=fld["excludeFromSearch"],
            )
            for fld in model_dict["flds"]
        ]

        # Convert template dictionaries to Template objects
        templates = [
            ModelTemplate(
                id=tmpl["id"],
                name=tmpl["name"],
                question_format=tmpl["qfmt"],
                answer_format=tmpl["afmt"],
                order=tmpl["ord"],
            )
            for tmpl in model_dict["tmpls"]
        ]

        # Create NoteModel instance
        return NoteModel(
            id=model_dict["id"],
            name=model_dict["name"],
            type=model_dict["type"],
            sort_field=model_dict["sortf"],
            deck_id=model_dict["did"],
            templates=templates,
            fields=fields,
            css=model_dict["css"],
            latex_pre=model_dict["latexPre"],
            latex_post=model_dict["latexPost"],
            latex_svg=model_dict["latexsvg"],
            requirements=model_dict["req"],
        )

    async def create(
        self,
        model_name: str,
        fields: list[str],
        templates: list[dict[str, str]],
        css: str = "",
        is_cloze: bool = False,
    ) -> NoteModel:
        """Create a new note model.

        Args:
            model_name: Name of the new model
            fields: List of field names in order
            templates: List of card templates, each with 'Name', 'Front', 'Back' keys
            css: Optional CSS styling (defaults to builtin CSS if empty)
            is_cloze: Whether this is a cloze deletion model

        Returns:
            The created NoteModel instance

        Raises:
            ModelAlreadyExistsError: If a model with this name already exists
            RuntimeError: For other AnkiConnect errors

        Example:
            >>> templates = [
            ...     {
            ...         "Name": "Card 1",
            ...         "Front": "{{Field1}}",
            ...         "Back": "{{FrontSide}}<hr>{{Field2}}"
            ...     }
            ... ]
            >>> await client.models.create(
            ...     model_name="My Model",
            ...     fields=["Field1", "Field2"],
            ...     templates=templates
            ... )
        """
        try:
            model_dict = await self._client._invoke(
                "createModel",
                params={
                    "modelName": model_name,
                    "inOrderFields": fields,
                    "css": css,
                    "isCloze": is_cloze,
                    "cardTemplates": templates,
                },
            )
        except RuntimeError as exc_:
            error_msg = str(exc_)
            if "already exists" in error_msg.lower():
                raise ModelAlreadyExists(
                    f"Model '{model_name}' already exists"
                ) from exc_
            raise
        else:
            return self._model_dict_to_notemodel(model_dict)

    async def update_templates(self, model_name: str, templates: list[ModelTemplate]):
        """Update the templates of a note model.

        Args:
            model_name: The name of the note model
            templates: List of ModelTemplate instances with updated templates

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        existing_templates = await self._client._invoke(
            "modelTemplates",
            params={
                "modelName": model_name,
            },
        )
        front_to_tmpl_name = {
            tmpl["Front"]: name for name, tmpl in existing_templates.items()
        }
        for tmpl in templates:
            existing_name = front_to_tmpl_name.get(tmpl.question_format, None)
            # If no existing template has the same question format, we consider it a new template and add it.
            if existing_name is None:
                # Add new template
                await self._client._invoke(
                    "modelTemplateAdd",
                    params={
                        "modelName": model_name,
                        "template": {
                            "Name": tmpl.name,
                            "Front": tmpl.question_format,
                            "Back": tmpl.answer_format,
                        },
                    },
                )
                continue

            # If the question format matches an existing template, we consider it an update.
            if tmpl.name != existing_name:
                # Rename first
                await self._client._invoke(
                    "modelTemplateRename",
                    params={
                        "modelName": model_name,
                        "oldTemplateName": existing_name,
                        "newTemplateName": tmpl.name,
                    },
                )
            # Update
            await self._client._invoke(
                "updateModelTemplates",
                params={
                    "model": {
                        "name": model_name,
                        "templates": {
                            tmpl.name: {
                                "Front": tmpl.question_format,
                                "Back": tmpl.answer_format,
                            }
                        },
                    }
                },
            )

    async def update_styling(self, model_name: str, css: str) -> None:
        """Update the CSS styling of a note model.

        Args:
            model_name: The name of the note model
            css: The new CSS styling

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        await self._client._invoke(
            "updateModelStyling",
            params={
                "model": {
                    "name": model_name,
                    "css": css,
                }
            },
        )


class MediaClient:
    """Client for managing Anki media files."""

    def __init__(self, client: "AnkiConnectClient") -> None:
        """Initialize MediaClient.

        Args:
            client: The parent AnkiConnectClient instance
        """
        self._client = client

    async def store_file(self, filename: str, data: bytes) -> str:
        """Store a media file in Anki's media folder.

        Args:
            filename: Name of the file to store
            data: Binary content of the file

        Returns:
            The filename of the stored file

        Raises:
            RuntimeError: If AnkiConnect returns an error

        Note:
            To prevent Anki from removing files not used by any cards,
            prefix the filename with an underscore (e.g. "_config.txt")

        Example:
            >>> with open("image.png", "rb") as f:
            ...     data = f.read()
            >>> filename = await client.media.store_file("word_image.png", data)
        """

        encoded_data = base64.b64encode(data).decode("utf-8")
        return await self._client._invoke(
            "storeMediaFile",
            params={
                "filename": filename,
                "data": encoded_data,
            },
        )


class NoteClient:
    """Client for managing Anki notes."""

    def __init__(self, client: "AnkiConnectClient") -> None:
        """Initialize NoteClient.

        Args:
            client: The parent AnkiConnectClient instance
        """
        self._client = client

    async def create_deck(self, deck_name: str) -> int:
        """Create a new deck in Anki.

        Args:
            deck_name: Name of the deck to create

        Returns:
            The ID of the created deck

        """
        return await self._client._invoke("createDeck", params={"deck": deck_name})

    async def find(self, deck_name: str, unique_fields: dict[str, str]) -> int | None:
        """Query for a note ID based on unique field values.

        Args:
            deck_name: Name of the deck to search within
            unique_fields: Dictionary of field names and their unique values

        Returns:
            The ID of the matching note or None if no match is found

        Raises:
            RuntimeError: If AnkiConnect returns an error or if no matching note is found

        Example:
            >>> note_id = await client.notes.query(
            ...     deck_name="My Vocabulary",
            ...     unique_fields={"Front": "hello"}
            ... )
        """
        query_parts = [f'deck:"{deck_name}"']
        for field_, value in unique_fields.items():
            query_parts.append(f'{field_}:"{value}"')
        query_str = " ".join(query_parts)

        try:
            note_ids = await self._client._invoke(
                "findNotes", params={"query": query_str}
            )
        except RuntimeError:
            raise
        else:
            if not note_ids:
                return None
            if len(note_ids) > 1:
                raise KeyError(
                    f"Expected exactly one note matching {unique_fields} in deck '{deck_name}', but found {len(note_ids)}"
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
        """Add a new note to Anki.

        Args:
            deck_name: Name of the deck to add the note to
            model_name: Name of the note model/type
            fields: Dictionary mapping field names to their values
            tags: Optional list of tags to add to the note

        Returns:
            The ID of the created note

        Raises:
            RuntimeError: If AnkiConnect returns an error

        Example:
            >>> note_id = await client.notes.add(
            ...     deck_name="My Vocabulary",
            ...     model_name="Basic",
            ...     fields={
            ...         "Front": "hello",
            ...         "Back": "你好"
            ...     },
            ...     tags=["chinese", "greetings"]
            ... )
        """
        note_data = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags or [],
            "options": {"allowDuplicate": allow_duplicate},
        }

        try:
            return await self._client._invoke("addNote", params={"note": note_data})
        except RuntimeError as e:
            error_msg = str(e)
            if error_msg.startswith("model was not found"):
                raise ModelNotFound(f"Model '{model_name}' not found") from e
            raise

    async def update_fields(self, note_id: int, fields: dict[str, str]) -> None:
        """Update the fields of an existing note.

        Args:
            note_id: ID of the note to update
            fields: Dictionary of field names and their new values

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        note_data: dict[str, Any] = {"id": note_id, "fields": fields}
        await self._client._invoke("updateNote", params={"note": note_data})

    async def update_tags(self, note_id: int, tags: list[str]) -> None:
        """Update the tags of an existing note.

        Args:
            note_id: ID of the note to update
            tags: List of tags to replace existing tags

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        note_data: dict[str, Any] = {"id": note_id, "tags": tags}
        await self._client._invoke("updateNote", params={"note": note_data})

    async def replace_tag_in_all_notes(self, to_replace: str, replacement: str) -> None:
        """Replace a tag with another tag across all notes.

        Args:
            to_replace: The tag to be replaced
            replacement: The tag to replace with

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        await self._client._invoke(
            "replaceTagsInAllNotes",
            params={
                "tag_to_replace": to_replace,
                "replace_with_tag": replacement,
            },
        )

    async def clear_all_unused_tags(self) -> None:
        """Clear all tags that are not currently used by any notes.

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        await self._client._invoke("clearUnusedTags")


class AnkiConnectClient:
    """Client for interacting with AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765") -> None:
        """Initialize AnkiConnect client.

        Args:
            url: AnkiConnect server URL
        """
        self._url = url
        self.models = ModelClient(self)
        self.notes = NoteClient(self)
        self.media = MediaClient(self)

    async def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """Invoke an AnkiConnect action.

        Args:
            action: The action to perform
            params: Parameters for the action

        Returns:
            The result from AnkiConnect

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        payload = {"action": action, "version": 6}
        if params is not None:
            payload["params"] = params

        session = get_session()
        async with session.post(self._url, json=payload) as response:
            result = await response.json()
        error = result["error"]
        if error is not None:
            raise RuntimeError(f"AnkiConnect error: {error}")

        return result["result"]
