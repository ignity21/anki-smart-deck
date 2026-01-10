# AnkiSmartDeck

> 🤖 AI-powered Anki vocabulary card generator using Google's suite of APIs

## 📖 About

AnkiSmartDeck is an automated Anki flashcard generator that leverages Google's ecosystem of APIs to create comprehensive vocabulary cards. It automatically fetches pronunciations, definitions, examples, images, and audio, then syncs directly with Anki through AnkiConnect plugin.

## ✨ Features

- 🤖 **Google AI Integration** - Powered by Google's Generative AI API for high-quality definitions and examples
- 🔊 **Audio Generation** - Text-to-Speech using Google Cloud TTS API for both US and UK pronunciations
- 🖼️ **Smart Image Search** - Automatic image retrieval via Google Custom Search API
- 🔄 **Direct Anki Sync** - Seamless integration with Anki through AnkiConnect plugin
- 📝 **Dual-Direction Cards** - Supports both word→definition and definition→word learning modes
- 🎨 **Beautiful Templates** - Built-in Light/Dark mode responsive card templates
- ⚡ **Batch Processing** - Generate multiple cards from word lists efficiently

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Anki with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed
- Google Cloud Platform account with API access

### Installation

```bash
# Clone the repository
git clone https://github.com/ignity21/anki-smart-deck.git
cd anki-smart-deck

# Install dependencies with uv
uv install

# Configure API credentials
cp .env.example .env
# Edit .env and add your Google API keys
```

### Configuration

Create a `.env` file with your Google API credentials:

```env
GOOGLE_AI_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_TTS_KEY=your_tts_api_key
GOOGLE_CUSTOM_SEARCH_KEY=your_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
ANKI_CONNECT_URL=http://localhost:8765
```

# Anki Smart Deck CLI - Usage Guide

## Overview

The Anki Smart Deck CLI is a powerful command-line tool for generating AI-powered Anki flashcards with automatic definitions, examples, pronunciations, audio, and images.

## Installation

```bash
# Install dependencies
pip install click rich --break-system-packages

# Make sure your services are configured
# (Google AI API key, Google TTS, Google Custom Search, etc.)
```

## Commands

### 1. `generate` - Single Word Generation

Generate a card for a single word.

**Basic usage:**
```bash
anki-deck generate serendipity
```

**Options:**
```bash
# Skip images
anki-deck generate serendipity --no-images

# Add custom tags
anki-deck generate ephemeral -t poetry -t beautiful-word

# Specify custom deck
anki-deck generate word --deck "My Deck::Vocabulary"

# Force create new card (even if exists)
anki-deck generate word --force

# All options combined
anki-deck generate eloquent -d "English::Advanced" -t literature --no-images --force
```

### 2. `interactive` - Interactive Mode

Add multiple words one by one with prompts.

**Basic usage:**
```bash
anki-deck interactive
```

**Features:**
- Prompts for each word
- Ask whether to include images for each word
- Continue adding or stop at any time
- Summary table at the end

**Options:**
```bash
# Start with images disabled by default
anki-deck interactive --no-images

# Add default tags to all words
anki-deck interactive -t chapter-5 -t vocabulary
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
anki-deck batch serendipity ephemeral eloquent
```

**Options:**
```bash
# Skip images for all words
anki-deck batch word1 word2 word3 --no-images

# Add tags to all cards
anki-deck batch word1 word2 -t batch-2024 -t important

# Custom deck
anki-deck batch word1 word2 --deck "English::GRE"
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
anki-deck from-file words.txt
```

**Options:**
```bash
# Skip images
anki-deck from-file vocabulary.txt --no-images

# Add tags
anki-deck from-file chapter-1.txt -t chapter-1 -t gre-prep

# Force update existing cards
anki-deck from-file words.txt --force
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
anki-deck generate serendipity -t emotions -t positive

# By source
anki-deck batch word1 word2 -t book-name -t chapter-3

# By difficulty
anki-deck generate word -t advanced -t gre
```

### 2. When to Skip Images

Skip images for:
- Abstract concepts (serendipity, ephemeral)
- Words that don't visualize well
- Fast batch processing

```bash
anki-deck generate abstract-word --no-images
```

### 3. Deck Organization

Use hierarchical deck names:
```bash
anki-deck generate word -d "English::Vocabulary::GRE"
anki-deck generate word -d "English::Business::Technical"
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
anki-deck from-file vocabulary.txt --no-images -t batch-import
```

### 5. Updating Cards

To update an existing card with new information:
```bash
anki-deck generate word --force
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
anki-deck from-file gre-words.txt -d "English::GRE" -t gre-vocab
```

### Example 2: Build Theme-Based Vocabulary
```bash
# Emotions
anki-deck batch elated melancholy serene anxious -t emotions

# Business terms
anki-deck batch synergy leverage paradigm -t business --no-images
```

### Example 3: Interactive Study Session
```bash
# Start interactive mode
anki-deck interactive -d "English::Daily" -t daily-vocab

# Then add words as you encounter them:
# - serendipity (with images)
# - ephemeral (skip images)
# - eloquent (with images)
```

## Advanced Usage

### Custom Note Type
If you've customized the note type:
```bash
anki-deck generate word -m "My Custom Note Type"
```

### Force Recreate All Cards
```bash
anki-deck from-file words.txt --force
```

### Multiple Tag Assignments
```bash
anki-deck generate word -t tag1 -t tag2 -t tag3
```

## Getting Help

```bash
# General help
anki-deck --help

# Command-specific help
anki-deck generate --help
anki-deck interactive --help
anki-deck batch --help
anki-deck from-file --help
```

## 📦 Tech Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **AI/ML**: Google Generative AI API (Gemini)
- **TTS**: Google Cloud Text-to-Speech API
- **Image Search**: Google Custom Search API
- **Anki Integration**: AnkiConnect
- **Card Templates**: HTML + CSS

## 🔧 API Services

### Google Generative AI
- Generate contextual definitions
- Create example sentences
- Suggest synonyms and mnemonics

### Google Cloud TTS
- High-quality audio generation
- Support for US and UK accents
- Multiple voice options

### Google Custom Search
- Retrieve relevant images
- Filter for educational content
- Safe search enabled

### AnkiConnect
- Direct communication with Anki
- Real-time card creation
- Deck management

## 📝 Usage Examples

### Single Word

```python
from ankismartdeck import CardGenerator

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
make type-check
```

## Documentation
- [Note Types](docs/NoteType.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details


