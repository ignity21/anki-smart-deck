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

- Python 3.10+
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

### Usage

```bash
# Generate a single card
uv run python main.py --word "serendipity"

# Batch process from file
uv run python main.py --file words.txt

# Specify deck name
uv run python main.py --word "vocabulary" --deck "My English Deck"
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
uv pip install -r requirements-dev.txt

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy .
```

## Documentation
- [Note Types](docs/NoteType.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details


