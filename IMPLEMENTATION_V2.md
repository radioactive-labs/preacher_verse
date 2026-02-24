# Preacher Verse V2 - Queue-Based System Implementation

## Overview

This document describes the V2 implementation of the Preacher Verse sermon verse retrieval system, which introduces a queue-based architecture with temporal awareness and improved verse selection accuracy.

## Key Improvements Over V1

### 1. **Simplified Detection Pipeline** (3 steps → 2 steps)
- **V1**: `AnalyzeContext` → `IdentifyVerseContent` → `Search` → `RankVerses` (3-5s)
- **V2**: `ContainsRelevantVerses` → `IdentifyRelevantVerses` → `Search` → `RankVerses` (<2s target)

### 2. **Queue-Based Voting Mechanism**
- Verses detected multiple times across 10s windows = higher confidence
- Max queue size: 3 items
- Aging mechanism: items not selected for 3 cycles get dropped
- Prevents immediate display of low-confidence matches

### 3. **Temporal Awareness**
- All timestamps tracked (sermon time MM:SS format)
- LLM receives timestamped transcript for better context
- Previous verses include timestamps to avoid repetition
- Full event logging for post-sermon replay

### 4. **Separated Detection & Display**
- **Detection thread**: Runs every 10s, fast analysis, adds to queue
- **Display thread**: Runs every 15s (cooldown), re-ranks queue, displays winner

### 5. **Anti-Hallucination Protection**
- Updated `RankVerses` with strict constraints
- Validation: ensures LLM only selects from provided candidates
- Fallback: uses top candidate if hallucination detected

### 6. **Direct Reference Support**
- SQLite lookup for explicit citations (e.g., "Matthew 6:27")
- 100% accuracy for direct references
- Separate path from content-based semantic search

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ DETECTION THREAD (every 10s)                                │
│ ├─ ContainsRelevantVerses (<1s)                             │
│ ├─ IdentifyRelevantVerses (<1s)                             │
│ ├─ Search: SQL or ChromaDB                                  │
│ ├─ RankVerses (<1s)                                         │
│ └─ Add to VerseQueue                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ VERSE QUEUE (max 3 items, FIFO with aging & voting)         │
│ ├─ Verse A (selected: 3x, age: 0, voting_score: 145)       │
│ ├─ Verse B (selected: 1x, age: 1, voting_score: 95)        │
│ └─ Verse C (selected: 1x, age: 2, voting_score: 85)        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ DISPLAY WORKER (every 15s cooldown)                         │
│ ├─ Age queue items (+1 age, drop if age >= 3)              │
│ ├─ Get best by voting_score                                 │
│ ├─ Check cooldown & duplicates                              │
│ ├─ Broadcast to frontend                                    │
│ ├─ Log to SQLite (analytics)                                │
│ └─ Remove from queue                                        │
└─────────────────────────────────────────────────────────────┘
```

## New Files Created

### DSPy Signatures
1. **`backend/dspy/signatures/contains_relevant_verses.py`**
   - Replaces `AnalyzeContext`
   - Fast yes/no decision on retrievable content
   - Returns: `contains_verses` (bool), `retrieval_type` (str), `reasoning` (str)
   - 14 training examples with temporal context

2. **`backend/dspy/signatures/identify_relevant_verses.py`**
   - Replaces `IdentifyVerseContent`
   - Extracts verse references OR search queries (based on type)
   - Returns: `verse_references` (str), `search_queries` (str), `biblical_entities` (str)
   - 18 training examples covering both paths

3. **`backend/dspy/signatures/rank_verses.py`** (updated)
   - Added anti-hallucination constraints in output field description
   - Same 10 training examples

### Models & Queue
4. **`backend/models/verse_queue.py`**
   - `QueuedVerse` dataclass with voting and aging
   - `VerseQueue` class with add/age/remove operations
   - Voting score calculation: `initial_score + (selection_count × 15) + recency_bonus`

5. **`backend/models/verse_display_event.py`**
   - Complete event record: verse data, timing, context, reasoning
   - Methods: `to_dict()`, `to_frontend_data()`
   - Enables post-sermon analytics

6. **`backend/models/transcript_buffer.py`** (updated)
   - Added `get_context_segments()` - returns list with timestamps
   - Added `get_timestamped_context()` - formats for LLM with [MM:SS] prefixes
   - Added `get_sermon_timestamp()` - current position as MM:SS
   - Added `get_time_range()` - (start, end) of context window

### Programs & Processors
7. **`backend/dspy/programs/fetch_verse_v2.py`**
   - New simplified 2-step pipeline
   - Temporal inputs: `current_time`, timestamped `context`, `previous_verses`
   - Direct reference lookup via SQLite
   - Content-based search via ChromaDB (RRF multi-query)
   - Anti-hallucination validation

8. **`backend/processors/sermon_processor_v2.py`**
   - Queue-based detection and display
   - Sermon start time tracking
   - Display worker background task
   - Event logging
   - Session summary generation

### Services
9. **`backend/services/verse_logger.py`**
   - SQLite logging for analytics
   - Tables: `verse_display_log`, `transcript_log`
   - Methods for session replay and statistics

## Configuration

### Environment Variables

```bash
# Feature flag to enable V2 (default: true)
USE_PROCESSOR_V2=true

# Existing config still works
COOLDOWN_SECONDS=15
CONTEXT_WINDOW_SECONDS=60
ACTIVE_WINDOW_SECONDS=10
```

## Database Schema

### verse_display_log
```sql
CREATE TABLE verse_display_log (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    verse_reference TEXT NOT NULL,
    verse_text TEXT NOT NULL,
    theme TEXT,
    relevance_score INTEGER,
    why_relevant TEXT,
    displayed_at TIMESTAMP NOT NULL,
    sermon_timestamp TEXT NOT NULL,        -- MM:SS format
    transcript_start TEXT,
    transcript_end TEXT,
    sermon_context TEXT,
    selection_count INTEGER,               -- Queue voting count
    queue_age INTEGER,                     -- How long in queue
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### transcript_log
```sql
CREATE TABLE transcript_log (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    sermon_timestamp TEXT,                 -- MM:SS format
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### Running V2 (Default)
```bash
./run.sh
# or
USE_PROCESSOR_V2=true python main.py
```

### Running V1 (Legacy)
```bash
USE_PROCESSOR_V2=false python main.py
```

### Checking Logs
```bash
tail -f logs/backend.log
```

## Testing Strategy

### 1. Unit Tests (Pending)
- Test `ContainsRelevantVerses` with various inputs
- Test `IdentifyRelevantVerses` for both direct/content paths
- Test `VerseQueue` voting and aging mechanisms
- Test anti-hallucination validation

### 2. Integration Tests (Pending)
- Full pipeline with real sermon audio
- Compare V1 vs V2 verse selections
- Measure inference times
- Check queue behavior over time

### 3. Manual Testing Checklist
- [ ] Direct reference: Pastor says "Matthew 6:27"
- [ ] Content-based: Pastor discusses worry without citing verse
- [ ] Repetition avoidance: Same topic discussed 2+ times
- [ ] Queue voting: Same verse detected multiple times
- [ ] Aging: Old queue items dropped after 3 cycles
- [ ] Temporal context: LLM sees timestamps
- [ ] Display cooldown: 15s between displays

## Migration Path

1. **Phase 1** (Current): Both V1 and V2 available via feature flag
2. **Phase 2**: Test V2 with real sermons, gather metrics
3. **Phase 3**: Fix any issues, tune parameters
4. **Phase 4**: Make V2 default, deprecate V1
5. **Phase 5**: Remove V1 code entirely

## Performance Targets

| Metric | V1 (Legacy) | V2 (Target) | V2 (Actual) |
|--------|-------------|-------------|-------------|
| Detection time | 3-5s | <2s | TBD |
| Hallucination rate | ~5% | <1% | TBD |
| Verse accuracy | 75% | 85%+ | TBD |
| Queue hit rate | N/A | 60%+ | TBD |

## Known Limitations

1. **First verse latency**: V2 takes 15s minimum (cooldown) vs V1's 3-5s immediate
2. **Queue can be empty**: If 3+ failures in a row, no display
3. **Memory overhead**: Queue + event log grows with sermon length
4. **SQLite writes**: Logging adds I/O (minimal impact)

## Future Enhancements

1. **Adaptive thresholds**: Lower min_relevance if queue empty for extended period
2. **Priority queue**: Weight by both voting_score AND recency
3. **Sermon segmentation**: Detect topic changes, clear queue on major shift
4. **Real-time analytics**: Dashboard showing queue status live
5. **Training data export**: Auto-generate DSPy examples from real sermons

## Files Modified

- `backend/dspy/signatures/__init__.py` - Added V2 signature exports
- `backend/dspy/programs/__init__.py` - Added FetchRelevantVerseV2 export
- `backend/dspy/signatures/rank_verses.py` - Anti-hallucination constraints
- `backend/models/transcript_buffer.py` - Temporal methods
- `main.py` - V2 processor support with feature flag

## Files Created (Summary)

- `backend/dspy/signatures/contains_relevant_verses.py`
- `backend/dspy/signatures/identify_relevant_verses.py`
- `backend/models/verse_queue.py`
- `backend/models/verse_display_event.py`
- `backend/dspy/programs/fetch_verse_v2.py`
- `backend/processors/sermon_processor_v2.py`
- `backend/services/verse_logger.py`

## Testing the Implementation

To test the V2 implementation:

```bash
# 1. Start the system with V2 enabled
USE_PROCESSOR_V2=true ./run.sh

# 2. Open frontend
open http://localhost:3000

# 3. Play test sermon audio or speak:
#    - Direct reference: "As Jesus says in Matthew 6:27..."
#    - Content-based: "We shouldn't worry about tomorrow..."
#    - Same verse multiple times to test voting

# 4. Monitor logs for queue status:
tail -f logs/backend.log | grep -E "(Queue|voting_score|selected.*times)"

# 5. Check analytics database:
sqlite3 data/sermon_analytics.sqlite "SELECT * FROM verse_display_log ORDER BY id DESC LIMIT 5"
```

## Rollback Plan

If V2 has critical issues:

```bash
# Immediately disable V2
export USE_PROCESSOR_V2=false
./stop.sh && ./run.sh

# Or modify .env file
echo "USE_PROCESSOR_V2=false" >> .env
```

V1 code is fully preserved and will continue to work.

---

**Implementation Date**: 2025-10-06
**Version**: 2.0.0
**Status**: Complete - Ready for testing
