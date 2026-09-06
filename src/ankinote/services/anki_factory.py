"""Single construction point for the Anki collection client.

Every UI page and CLI command builds its client through :func:`create_anki_client`
instead of instantiating a backend directly, so backend selection lives in one
place. Selection is driven by ``ANKI_BACKEND``:

- ``connect`` (default): talk to a running AnkiConnect server.
- ``collection``: operate on a local Anki collection in-process. Requires
  ``ANKI_COLLECTION_PATH``.
"""

from __future__ import annotations

from ankinote.config import envs
from ankinote.services.anki import AnkiCollectionClient, AnkiConnectClient

CONNECT_BACKEND = "connect"
COLLECTION_BACKEND = "collection"
_KNOWN_BACKENDS = (CONNECT_BACKEND, COLLECTION_BACKEND)


class AnkiBackendConfigError(Exception):
    """Raised when the Anki backend selection is misconfigured."""


def create_anki_client() -> AnkiCollectionClient:
    """Build the Anki client for the configured backend.

    Raises:
        AnkiBackendConfigError: If ``ANKI_BACKEND`` is unknown, or a backend's
            required configuration is missing.
    """
    backend = (envs.ANKI_BACKEND or CONNECT_BACKEND).strip().lower()

    if backend == CONNECT_BACKEND:
        return AnkiConnectClient()

    if backend == COLLECTION_BACKEND:
        if not envs.ANKI_COLLECTION_PATH:
            raise AnkiBackendConfigError(
                "ANKI_BACKEND=collection requires ANKI_COLLECTION_PATH to point "
                "at the Anki collection directory."
            )
        raise AnkiBackendConfigError(
            "The 'collection' Anki backend is not implemented yet."
        )

    raise AnkiBackendConfigError(
        f"Unknown ANKI_BACKEND {backend!r}; expected one of "
        f"{', '.join(_KNOWN_BACKENDS)}."
    )
