"""Private AnkiWeb credentials, separate from browser-facing sync state."""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import TypeAdapter


@dataclass(frozen=True, slots=True)
class SyncCredential:
    account: str
    hkey: str = field(repr=False)
    endpoint: str | None = field(default=None, repr=False)


def private_write(path: Path, data: bytes) -> None:
    """Atomically persist private data with mode 0600, including during creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


class CredentialStore:
    """Keep account binding after logout to prevent accidental account switching."""

    def __init__(self, collection_path: str) -> None:
        self.path = Path(f"{collection_path}.credentials.json")
        self._binding = Path(f"{collection_path}.account")
        self._adapter = TypeAdapter(SyncCredential)

    def check_account(self, account: str) -> None:
        digest = hashlib.sha256(account.strip().casefold().encode()).hexdigest()
        if self._binding.exists() and self._binding.read_text() != digest:
            raise ValueError("This collection is bound to a different AnkiWeb account")

    def bind(self, account: str) -> None:
        self.check_account(account)
        digest = hashlib.sha256(account.strip().casefold().encode()).hexdigest()
        private_write(self._binding, digest.encode())

    def load(self) -> SyncCredential | None:
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return None
        try:
            credential = self._adapter.validate_json(data)
        except ValueError:
            raise ValueError("Invalid AnkiWeb credential file") from None
        self.check_account(credential.account)
        os.chmod(self.path, 0o600)
        return credential

    def save(self, credential: SyncCredential) -> None:
        self.bind(credential.account)
        private_write(self.path, self._adapter.dump_json(credential))

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)
