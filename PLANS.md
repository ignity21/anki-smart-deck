# Future Plans

## 0. CLI reference (completed)

A reference file (`skills/ankinote-cli/SKILL.md`) documents the full `ankinote` CLI surface.
Any agent or human working in this repo can use it to understand how to operate
cards directly.

## 1. CLI Review

### Duplicated batch logic
The `batch` command in `word`, `phrase`, `sentence`, and `stem` share the same
pattern (RPM limiting, concurrency control, file reading). Extract a shared
`batch` decorator or mixin.

### Dead code
`src/ankinote/cli/math.py` and `src/ankinote/collections/math/` are no longer
registered in the CLI but still in the tree. Decide whether to keep or remove.

## 2. PyPI Release

### Prerequisites
- Dependencies: litellm, google-cloud-texttospeech, httpx, pydantic, etc.
  Install experience needs to be smooth.
- API key docs: GEMINI_API_KEY, GOOGLE_TTS_KEY, ANKI_CONNECT_URL
- AnkiConnect is an external dependency — users need to install the Anki addon
  separately.
- CLI and docs should be in English if targeting international users.

### Considerations
- Project is already structured with pyproject.toml, CLI entrypoint, version
- Public release means maintaining backward compatibility
- Consider a `--dry-run` mode that generates cards without pushing to Anki
