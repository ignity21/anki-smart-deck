---
name: ankinote-cli
description: Use the ankinote CLI to generate and push Anki cards. Use when the task involves creating, batching, or initializing Anki cards for vocabulary, sentences, phrases, or STEM topics through the ankinote command-line tool.
---

# Ankinote CLI

Generate AI-powered Anki cards from the terminal. Uses Gemini/DeepSeek via litellm for content generation, optionally generates diagrams via Gemini, and pushes cards to Anki through AnkiConnect.

## Prerequisites

- Anki running with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- Environment variables: `GEMINI_API_KEY`, `ANKI_CONNECT_URL` (defaults to `http://localhost:8765`)
- Project installed: `uv sync`

## Commands

### Global structure

```
ankinote [--version] <collection> <command> [args...]
```

Four collections: `word`, `phrase`, `sentence`, `stem`. Each has three subcommands: `add`, `batch`, `init`.

Run `uv run ankinote --help` for the full list.

### Collection overview

| Collection | Purpose | Input | Image support |
|---|---|---|---|
| `word` | Vocabulary cards (word + definition) | A single word per card | Yes (generated) |
| `phrase` | Phrase/sentence cards | A phrase or short sentence | No |
| `sentence` | Production-direction sentence cards (V2) | A sentence in the native language; AI generates the target-language version on the back | No |
| `stem` | STEM knowledge cards (Math, CS, Finance, ML, ...) | Any question or concept (e.g. "What is a derivative?", "State Bayes' theorem") | Yes (diagrams) |

### Common options

All collections accept `--llm` to override the default model (currently DeepSeek V4 Flash).
Collections with image support accept `--image-model` (defaults to Gemini 2.5 Flash Image).
Language-aware collections (`word`, `phrase`, `sentence`) accept `--native` and `--target`:

```
--native [English|Chinese(Simplified)|Chinese(Traditional)|Japanese|French|Spanish|German|Korean|other]
--target [English|Chinese(Simplified)|Chinese(Traditional)|Japanese|French|Spanish|German|Korean|other]
```

Defaults: `--native Chinese(Simplified) --target English`.

All collections accept `--thinking [off|low|medium|high|default]` to override the
model's extended-thinking level for that run. Omitted, `word`/`phrase`/`sentence`
disable thinking and `stem` uses the provider default. `off` disables it,
`default` forces the provider default, and the named levels are passed through as
`reasoning_effort` (the current DeepSeek routing only distinguishes on/off).

### `add` — Single card

```
uv run ankinote word add <word>
uv run ankinote sentence add <sentence>
uv run ankinote phrase add <phrase>
uv run ankinote stem add <topic>
```

### `batch` — Multiple cards

```
uv run ankinote word batch <word1> <word2> ...
uv run ankinote sentence batch --file sentences.txt
uv run ankinote phrase batch "call off" --file more.txt
uv run ankinote stem batch --file topics.txt
```

Accepts inline arguments, `--file <path>` (one item per line), or both.
Use `--rpm <N>` to set the rate limit (defaults vary by collection: 8 for word, 60 for sentence/phrase/stem).

### `init` — Create note type and deck

```
uv run ankinote word init
uv run ankinote sentence init
uv run ankinote phrase init
uv run ankinote stem init
```

Must be run once before adding cards to a new collection. Creates the note type and deck in Anki.

### Stem-specific options

```
--image-size <pixels>    # Image size in pixels (square)
--image-model <id>       # Image model for diagram generation
```

## Workflows

### First-time setup

```bash
uv run ankinote word init
uv run ankinote word add serendipity
```

### Batch import from file

```bash
cat > words.txt << EOF
ephemeral
eloquent
ubiquitous
EOF
uv run ankinote word batch --file words.txt --rpm 30
```

### STEM card with diagram

```bash
uv run ankinote stem add "What is a derivative?" --image-size 1024
```

## Troubleshooting

- **"AnkiConnect not available"**: Make sure Anki is running and the AnkiConnect addon is installed
- **"API key not found"**: Check `GEMINI_API_KEY` is set in the environment or `.env` file
- **Model not found**: The default model strings resolve to provider-specific IDs. Override with `--llm` if needed
