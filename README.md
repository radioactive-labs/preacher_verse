# Preacher Verse

Real-time sermon verse retrieval system. Listens to live preaching, detects biblical themes using AI, and displays relevant Bible verses to the congregation.

## How It Works

```
Browser Microphone (Web Speech API)
         ↓
   HTTP API (transcript)
         ↓
   TranscriptBuffer (60s context)
         ↓
   FetchRelevantVerse (DSPy pipeline)
   ├── ContainsRelevantVerses (fast filter)
   ├── IdentifyRelevantVerses (extract refs/queries)
   └── ChromaDB search (RRF multi-query)
         ↓
   VerseQueue (voting + aging)
         ↓
   Display Worker (re-ranks with RankVerses)
         ↓
   WebSocket → React Frontend
```

## Architecture

**Queue-Based Processing:**
- Detection runs every 10 seconds, adds candidates to queue
- Display worker polls every 1 second, respects cooldown
- Queue supports voting (same verse detected multiple times = higher priority)
- Verses age out if not displayed

**DSPy Pipeline (2-step + ranking):**
1. `ContainsRelevantVerses` - Fast yes/no: does this segment warrant a verse?
2. `IdentifyRelevantVerses` - Extract direct references OR semantic search queries
3. `RankVerses` - At display time, re-rank queue candidates against current context

## Tech Stack

| Component | Technology |
|-----------|------------|
| Speech-to-Text | Browser Web Speech API |
| LLM | Gemini 2.0 Flash via DSPy |
| Embeddings | SentenceTransformer `all-mpnet-base-v2` |
| Vector Search | ChromaDB (local) |
| Backend | Python AsyncIO + aiohttp |
| Frontend | React |
| Real-time | WebSocket |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- API Keys:
  - [Deepgram](https://deepgram.com) - Speech-to-text (optional, for direct audio)
  - [Google AI Studio](https://aistudio.google.com) - Gemini API

### One-Command Setup

```bash
./scripts/setup.sh
```

This will:
1. Create virtual environment
2. Install Python and Node dependencies
3. Check for `.env` and prompt for API keys
4. Populate Bible verses with enrichment (~30 min first run)
5. Test all connections

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Populate Bible verses
python scripts/populate_verses.py

# Test connections
python scripts/test_connection.py
```

### Environment Variables

```bash
# Required
DEEPGRAM_API_KEY=your_key    # For direct audio transcription
GEMINI_API_KEY=your_key      # For LLM processing

# Optional (defaults shown)
COOLDOWN_SECONDS=30              # Min time between displayed verses
RANKING_CONFIDENCE_THRESHOLD=75  # Min score to display verse (0-100)
ACTIVE_WINDOW_SECONDS=10         # Detection interval
CONTEXT_WINDOW_SECONDS=60        # Transcript context window
```

### Run

**Quick start (both backend and frontend):**
```bash
./scripts/run.sh
```

**Or manually:**

Terminal 1 - Backend:
```bash
source venv/bin/activate
python main.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

### Endpoints

- **Frontend:** http://localhost:3000
- **HTTP API:** http://localhost:8080
- **WebSocket:** ws://localhost:8765

### Connect Audio

1. Open http://localhost:3000
2. Click "Connect Microphone" in the Audio Control panel
3. Allow microphone access when prompted
4. Speak - verses will appear automatically

## Configuration

Edit `config.yaml` for detailed settings:

```yaml
verse_retrieval:
  top_k_candidates: 5      # Candidates per search
  min_relevance_score: 75  # Display threshold

transcript:
  context_window_seconds: 60
  active_window_seconds: 10

theme_detection:
  min_words: 15  # Minimum words before detection
```

## Project Structure

```
preacher_verse/
├── backend/
│   ├── dspy/
│   │   ├── programs/
│   │   │   └── fetch_verse.py    # Main DSPy pipeline
│   │   └── signatures/           # DSPy signatures
│   │       ├── contains_relevant_verses.py
│   │       ├── identify_relevant_verses.py
│   │       └── rank_verses.py
│   ├── models/
│   │   ├── transcript_buffer.py  # Rolling window transcript
│   │   ├── verse_queue.py        # Queue with voting
│   │   └── verse_display_event.py
│   ├── processors/
│   │   └── sermon_processor.py   # Main orchestration
│   ├── api/
│   │   └── http_server.py        # HTTP API for transcripts
│   ├── services/
│   │   ├── websocket_server.py
│   │   └── verse_enricher.py
│   └── utils/
│       ├── config.py
│       └── logger.py
├── frontend/
│   └── src/
│       ├── App.js
│       └── components/
│           ├── VerseDisplay.js
│           ├── VersesPanel.js
│           ├── TranscriptPanel.js
│           └── AudioConfigPanel.js
├── data/
│   ├── chromadb/          # Vector embeddings (31k verses)
│   └── bible-kjv/         # Source JSON files
├── scripts/
│   ├── setup.sh           # Full setup
│   ├── run.sh             # Start system
│   ├── populate_verses.py # Load Bible into ChromaDB
│   └── test_connection.py # Test all services
├── main.py                # Entry point
├── config.yaml
└── requirements.txt
```

## How Detection Works

1. **Transcript arrives** from browser (Web Speech API)
2. **Buffer accumulates** 60 seconds of context with timestamps
3. **Every 10 seconds**, detection runs:
   - `ContainsRelevantVerses`: Should we look for a verse? (fast filter)
   - `IdentifyRelevantVerses`: Extract references OR search queries
   - ChromaDB search with RRF (Reciprocal Rank Fusion) across multiple queries
4. **Top 3 candidates** added to queue with voting scores
5. **Display worker** (separate loop):
   - Waits for cooldown (30s default)
   - Re-ranks queue with `RankVerses` against current context
   - Displays highest-scoring verse above threshold
   - Removes from queue, marks as recently shown

## Cost Estimate

- **Gemini**: Free tier (1,500 requests/day) or ~$0.075/1M tokens
- **ChromaDB**: Free (local)
- **Browser Speech API**: Free

**Monthly estimate**: ~$0-5 for typical usage

## Scripts

```bash
# Full setup (venv, deps, populate, test)
./scripts/setup.sh

# Start both backend and frontend
./scripts/run.sh

# Populate verses (enrichment enabled by default)
./scripts/populate.sh

# Populate without enrichment (faster)
./scripts/populate.sh --no-enrich

# Test connections
python scripts/test_connection.py
```

## Troubleshooting

**No verses appearing:**
- Check `RANKING_CONFIDENCE_THRESHOLD` - lower it (e.g., 60) for more verses
- Check `COOLDOWN_SECONDS` - verses won't show faster than this interval
- Verify ChromaDB has data: `python scripts/test_connection.py`

**Microphone not working:**
- Ensure you're using Chrome or Edge (Web Speech API support)
- Check browser permissions for microphone access
- Try refreshing the page

**High latency:**
- Detection targets <2s inference time
- If slow, check Gemini API response times
- Consider reducing `top_k_candidates`

## License

MIT
