from dataclasses import dataclass, field
from typing import Any

from ankinote.utils import get_session


@dataclass
class Field:
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
class Template:
    """Represents a card template in an Anki note model."""

    id: int
    name: str
    question_format: str = field(doc="HTML/template for the question side")
    answer_format: str = field(doc="HTML/template for the answer side")
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
    templates: list[Template] = field(default_factory=list, repr=False)
    fields: list[Field] = field(default_factory=list)
    css: str = field(doc="CSS styling for cards", default="", repr=False)
    latex_pre: str = field(doc="LaTeX preamble", default="", repr=False)
    latex_post: str = field(doc="LaTeX postamble", default="", repr=False)
    latex_svg: bool = field(doc="Whether to render LaTeX as SVG", default=False)
    requirements: list[list[Any]] = field(
        doc="Card generation requirements", default_factory=list
    )


class AnkiConnectClient:
    """Client for interacting with AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765") -> None:
        """Initialize AnkiConnect client.

        Args:
            url: AnkiConnect server URL
        """
        self._url = url

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
        session = await get_session()

        async with session.post(self._url, json=payload) as response:
            result = await response.json()
        error = result["error"]
        if error is not None:
            raise RuntimeError(f"AnkiConnect error: {error}")

        return result["result"]

    async def list_models(self) -> list[str]:
        """List all note types (models) in Anki.

        Returns:
            List of note type
        """
        return await self._invoke("modelNames")

    async def find_model(self, model_name: str) -> NoteModel:
        """Find a note type (model) by name.

        Args:
            model_name: The note type name

        Returns:
            NoteModel instance

        Raises:
            ValueError: If model not found or multiple models found
        """
        model_list = await self._invoke(
            "findModelsByName",
            params={
                "modelNames": [
                    model_name,
                ]
            },
        )

        if not model_list:
            raise ValueError(f"Model '{model_name}' not found")

        if len(model_list) > 1:
            raise ValueError(
                f"Multiple models found for name '{model_name}': {len(model_list)}"
            )

        model_dict = model_list[0]

        # Convert field dictionaries to Field objects
        fields = [
            Field(
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
            Template(
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
