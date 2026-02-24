# Preacher Verse

Real-time sermon verse retrieval system. Listens to live preaching via WebRTC, detects biblical themes using AI, and displays relevant Bible verses to the congregation.

## How It Works

```
Daily.co (WebRTC Audio)
         ↓
   Deepgram STT (nova-2)
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
| Audio | Daily.co WebRTC |
| Speech-to-Text | Deepgram nova-2 |
| LLM | Gemini 2.0 Flash via DSPy |
| Embeddings | SentenceTransformer `all-mpnet-base-v2` |
| Vector Search | ChromaDB (local) |
| Direct Lookup | SQLite |
| Pipeline | Pipecat |
| Backend | Python AsyncIO |
| Frontend | React |
| Real-time | WebSocket |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- API Keys:
  - [Deepgram](https://deepgram.com) - Speech-to-text
  - [Google AI Studio](https://aistudio.google.com) - Gemini API
  - [Daily.co](https://daily.co) - WebRTC rooms

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# Required
DEEPGRAM_API_KEY=your_key
GEMINI_API_KEY=your_key
DAILY_API_KEY=your_key

# Optional (defaults shown)
COOLDOWN_SECONDS=30              # Min time between displayed verses
RANKING_CONFIDENCE_THRESHOLD=75  # Min score to display verse (0-100)
ACTIVE_WINDOW_SECONDS=10         # Detection interval
CONTEXT_WINDOW_SECONDS=60        # Transcript context window
```

### Populate Bible Data

The system needs Bible verses in ChromaDB. First run:

```bash
python scripts/populate_verses.py
```

This loads the full KJV Bible (31,102 verses) with embeddings. Takes ~30 minutes on first run.

### Run

**Terminal 1 - Backend:**
```bash
python main.py
```

This starts:
- WebSocket server on `ws://localhost:8765`
- Daily bot endpoint on `http://localhost:7860`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

Opens `http://localhost:3000`

### Connect Audio

1. Create a Daily.co room at https://dashboard.daily.co
2. Join the room from browser/device with microphone
3. The bot auto-joins and starts processing audio

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
│   ├── bible-kjv/         # Source JSON files
│   └── optimized_signatures/  # GEPA-optimized prompts
├── scripts/
│   ├── populate_verses.py # Load Bible into ChromaDB
│   └── test_connection.py # Test all services
├── main.py                # Entry point
├── config.yaml
└── requirements.txt
```

## How Detection Works

1. **Transcript arrives** from Deepgram (streaming STT)
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

- **Deepgram**: ~$0.26/hour of audio
- **Gemini**: Free tier (1,500 requests/day) or ~$0.075/1M tokens
- **Daily.co**: Free tier includes 10,000 participant-minutes/month
- **ChromaDB**: Free (local)

**Monthly estimate**: ~$5-10 for weekly services

## Scripts

```bash
# Populate Bible verses (first time setup)
python scripts/populate_verses.py

# Test all service connections
python scripts/test_connection.py

# Run with enrichment (slower, better search quality)
python scripts/populate_verses.py --enrich
```

## Troubleshooting

**No verses appearing:**
- Check `RANKING_CONFIDENCE_THRESHOLD` - lower it (e.g., 60) for more verses
- Check `COOLDOWN_SECONDS` - verses won't show faster than this interval
- Verify ChromaDB has data: `python scripts/test_connection.py`

**Deepgram not transcribing:**
- Check `DEEPGRAM_API_KEY` is valid
- Ensure Daily room has audio input enabled
- Check logs for WebSocket connection errors

**High latency:**
- Detection targets <2s inference time
- If slow, check Gemini API response times
- Consider reducing `top_k_candidates`

## License

MIT
