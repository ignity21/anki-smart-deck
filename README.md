# ankinote

<p align="center">
  <a href="https://pypi.org/project/ankinote-ai/"><img src="https://img.shields.io/pypi/v/ankinote-ai?color=blue&logo=pypi&logoColor=white" alt="PyPI version"></a>
  <a href="https://pypi.org/project/ankinote-ai/"><img src="https://img.shields.io/pypi/pyversions/ankinote-ai?color=blue&logo=python&logoColor=white" alt="Python versions"></a>
  <a href="https://github.com/ignity21/ankinote-ai/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/ankinote-ai?color=blue" alt="License"></a>
  <a href="https://codecov.io/gh/ignity21/ankinote-ai"><img src="https://img.shields.io/codecov/c/github/ignity21/ankinote-ai?logo=codecov&logoColor=white" alt="Codecov"></a>
</p>

> AI-powered Anki card generator — vocabulary, phrases, sentences, and STEM concepts

## 📖 About

ankinote is an automated Anki flashcard generator that uses litellm to support a wide range of AI providers — Gemini, GPT, Claude, DeepSeek, and more — for generating definitions, examples, mnemonics, and images, then syncs directly with Anki through AnkiConnect.

## ✨ Features

- 🤖 **Multi-Provider AI** - Powered by litellm, supporting Gemini, GPT, Claude, DeepSeek, and more for text and image generation
- 🔊 **Audio Generation** - Text-to-Speech using Google Cloud TTS API
- 🖼️ **AI Image Generation** - Automatic image generation via Google AI (Gemini)
- 🔄 **Direct Anki Sync** - Seamless integration with Anki through AnkiConnect plugin
- 📝 **Dual-Direction Cards** - Supports both word→definition and definition→word learning modes
- 🎨 **Beautiful Templates** - Built-in Light/Dark mode responsive card templates
- ⚡ **Batch Processing** - Generate multiple cards from word lists efficiently
- 🌐 **Multi-Language** - Japanese, English (US), and extensible for more languages
- 🧮 **STEM Concepts** - Math, science, and programming concept cards with MathJax rendering

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Anki with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- An API key for at least one AI provider (see Configuration below)

### Installation

```bash
# Clone the repository
git clone https://github.com/ignity21/ankinote-ai.git
cd ankinote-ai

# Install dependencies with uv
uv sync

# Configure API credentials
cp .env.example .env
# Edit .env and add your API keys
```

### Configuration

Create a `.env` file with your API keys. At minimum, you need one AI provider key and the Google TTS key:

```env
# At least one AI provider (for text and image generation)
GEMINI_API_KEY=your_gemini_key
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# DEEPSEEK_API_KEY=sk-...

# Google Cloud TTS (for audio generation)
GOOGLE_TTS_KEY=your_tts_api_key

# AnkiConnect (defaults to http://localhost:8765)
ANKI_CONNECT_URL=http://localhost:8765
```

# ankinote CLI - Usage Guide

## Overview

The ankinote CLI is a powerful command-line tool for generating AI-powered Anki flashcards with automatic definitions, examples, pronunciations, audio, and images.

## Installation

```bash
# Install dependencies
pip install click rich --break-system-packages

# Make sure your services are configured
# (Google AI API key, Google TTS, an AI provider, etc.)
```

## Commands

### 1. `generate` - Single Word Generation

Generate a card for a single word.

**Basic usage:**
```bash
ankinote generate serendipity
```

**Options:**
```bash
# Skip images
ankinote generate serendipity --no-images

# Add custom tags
ankinote generate ephemeral -t poetry -t beautiful-word

# Specify custom deck
ankinote generate word --deck "My Deck::Vocabulary"

# Force create new card (even if exists)
ankinote generate word --force

# All options combined
ankinote generate eloquent -d "English::Advanced" -t literature --no-images --force
```

### 2. `interactive` - Interactive Mode

Add multiple words one by one with prompts.

**Basic usage:**
```bash
ankinote interactive
```

**Features:**
- Prompts for each word
- Ask whether to include images for each word
- Continue adding or stop at any time
- Summary table at the end

**Options:**
```bash
# Start with images disabled by default
ankinote interactive --no-images

# Add default tags to all words
ankinote interactive -t chapter-5 -t vocabulary
```

**Example session:**
```
Enter a word: serendipity
Include images for this word? [Y/n]: y
✓ Created! Note ID: 12345

Add another word? [Y/n]: y

Enter a word: ephemeral
Include images for this word? [Y/n]: n
✓ Created! Note ID: 12346

Add another word? [Y/n]: n

Generation Summary
┌──────────────┬──────────┬─────────┐
│ Word         │ Status   │ Note ID │
├──────────────┼──────────┼─────────┤
│ serendipity  │ ✓ Created│ 12345   │
│ ephemeral    │ ✓ Created│ 12346   │
└──────────────┴──────────┴─────────┘
```

### 3. `batch` - Batch Generation

Generate multiple cards at once from command-line arguments.

**Basic usage:**
```bash
ankinote batch serendipity ephemeral eloquent
```

**Options:**
```bash
# Skip images for all words
ankinote batch word1 word2 word3 --no-images

# Add tags to all cards
ankinote batch word1 word2 -t batch-2024 -t important

# Custom deck
ankinote batch word1 word2 --deck "English::GRE"
```

### 4. `from-file` - Generate from File

Generate cards from a word list file.

**File format:**
```txt
# comments start with #
serendipity
ephemeral
eloquent

# empty lines are ignored

ubiquitous
```

**Basic usage:**
```bash
ankinote from-file words.txt
```

**Options:**
```bash
# Skip images
ankinote from-file vocabulary.txt --no-images

# Add tags
ankinote from-file chapter-1.txt -t chapter-1 -t gre-prep

# Force update existing cards
ankinote from-file words.txt --force
```

## Common Options

All commands support these options:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--deck` | `-d` | Target Anki deck name | `English::AI Words` |
| `--model` | `-m` | Note type/model name | `AI Word (R)` |
| `--no-images` | | Skip image search | Include images |
| `--tags` | `-t` | Add custom tags (multiple) | None |
| `--force` | `-f` | Force create new cards | Update existing |

## Tips

### 1. Organizing with Tags

Use tags to organize your vocabulary:
```bash
# By topic
ankinote generate serendipity -t emotions -t positive

# By source
ankinote batch word1 word2 -t book-name -t chapter-3

# By difficulty
ankinote generate word -t advanced -t gre
```

### 2. When to Skip Images

Skip images for:
- Abstract concepts (serendipity, ephemeral)
- Words that don't visualize well
- Fast batch processing

```bash
ankinote generate abstract-word --no-images
```

### 3. Deck Organization

Use hierarchical deck names:
```bash
ankinote generate word -d "English::Vocabulary::GRE"
ankinote generate word -d "English::Business::Technical"
```

### 4. Batch Processing Large Lists

For large vocabulary lists:
```bash
# Create a file with all words
cat > vocabulary.txt << EOF
word1
word2
word3
EOF

# Generate all at once
ankinote from-file vocabulary.txt --no-images -t batch-import
```

### 5. Updating Cards

To update an existing card with new information:
```bash
ankinote generate word --force
```

## Troubleshooting

### Error: "AnkiConnect not available"
- Make sure Anki is running
- Check that AnkiConnect add-on is installed
- Verify AnkiConnect is listening on port 8765

### Error: "No images found"
- Some abstract words may not have good images
- Use `--no-images` flag to skip
- Or continue without images when prompted

### Error: "API key not found"
- Check your configuration file
- Ensure environment variables are set
- Verify API keys are valid

## Examples

### Example 1: Study GRE Vocabulary
```bash
# Create a GRE word list file
cat > gre-words.txt << EOF
ubiquitous
ephemeral
eloquent
serendipity
EOF

# Generate all cards
ankinote from-file gre-words.txt -d "English::GRE" -t gre-vocab
```

### Example 2: Build Theme-Based Vocabulary
```bash
# Emotions
ankinote batch elated melancholy serene anxious -t emotions

# Business terms
ankinote batch synergy leverage paradigm -t business --no-images
```

### Example 3: Interactive Study Session
```bash
# Start interactive mode
ankinote interactive -d "English::Daily" -t daily-vocab

# Then add words as you encounter them:
# - serendipity (with images)
# - ephemeral (skip images)
# - eloquent (with images)
```

## Advanced Usage

### Custom Note Type
If you've customized the note type:
```bash
ankinote generate word -m "My Custom Note Type"
```

### Force Recreate All Cards
```bash
ankinote from-file words.txt --force
```

### Multiple Tag Assignments
```bash
ankinote generate word -t tag1 -t tag2 -t tag3
```

## Getting Help

```bash
# General help
ankinote --help

# Command-specific help
ankinote generate --help
ankinote interactive --help
ankinote batch --help
ankinote from-file --help
```

## 📦 Tech Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **AI/ML**: litellm (Gemini, GPT, Claude, DeepSeek, etc.)
- **TTS**: Google Cloud Text-to-Speech API
- **Image Generation**: Google AI (Gemini)
- **Anki Integration**: AnkiConnect
- **Card Templates**: HTML + CSS

## 🔧 API Services

### AI Provider (via litellm)
- Text generation for definitions, examples, and mnemonics
- Image generation (Gemini) for card visuals
- Supports Gemini, GPT, Claude, DeepSeek, Qwen, and more

### Google Cloud TTS
- High-quality audio generation
- Multiple voice options

### AnkiConnect
- Direct communication with Anki
- Real-time card creation
- Deck management

## 📝 Usage Examples

### Single Word

```python
from ankinote import CardGenerator

generator = CardGenerator()
card = generator.generate("ephemeral")
generator.add_to_anki(card, deck="Vocabulary")
```

### Batch Processing

```python
words = ["ephemeral", "serendipity", "eloquent"]
for word in words:
    card = generator.generate(word)
    generator.add_to_anki(card)
```

## 🛠️ Development

```bash
# Install development dependencies
uv sync

# Run tests
make test

# Format code
make format

# Type checking
make check
```

## Documentation
- [Note Types](docs/NoteType.md)
- [Codex Skill](skills/ankinote-cli/SKILL.md) — for using ankinote with AI coding assistants

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details


