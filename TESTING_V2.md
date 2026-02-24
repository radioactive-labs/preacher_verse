# Testing Preacher Verse V2

## Quick Start

```bash
# Enable V2 and start the system
export USE_PROCESSOR_V2=true
./run.sh

# In another terminal, watch the logs
tail -f logs/backend.log | grep -E "(Queue|Verse displayed|voting_score)"
```

## Test Scenarios

### Scenario 1: Direct Reference
**Pastor says**: "As Jesus teaches in Matthew 6:27, can any of you by worrying add a single hour to your life?"

**Expected behavior**:
1. ContainsRelevantVerses: `contains_verses=True`, `retrieval_type="direct_reference"`
2. IdentifyRelevantVerses: `verse_references="Matthew 6:27"`
3. Direct SQL lookup finds verse
4. Added to queue with score 100
5. Displayed after 15s cooldown

**Check**:
```bash
# Should see in logs:
# "Retrieval type: direct_reference"
# "Looking up direct references: Matthew 6:27"
# "Added new verse to queue: Matthew 6:27 (score: 100)"
# "✓ Verse displayed: Matthew 6:27 (voting_score: 130)"
```

### Scenario 2: Content-Based Search
**Pastor says**: "Brothers and sisters, we are saved by grace through faith, not by our own works."

**Expected behavior**:
1. ContainsRelevantVerses: `contains_verses=True`, `retrieval_type="content_based"`
2. IdentifyRelevantVerses: `search_queries="saved by grace through faith not works; ..."`
3. ChromaDB semantic search finds Ephesians 2:8-9
4. Added to queue
5. Displayed after cooldown

**Check**:
```bash
# Should see in logs:
# "Retrieval type: content_based"
# "Search queries: saved by grace through faith not works..."
# "Found 5 candidates"
# "✓ Verse displayed: Ephesians 2:8-9"
```

### Scenario 3: Voting Mechanism (Same Verse Multiple Times)
**Test**: Say the same biblical phrase 3 times in 30 seconds

Example:
1. [00:10] "Faith without works is dead"
2. [00:20] "True faith produces fruit - faith without works is dead"
3. [00:30] "As James says, faith without works is dead"

**Expected behavior**:
- First detection: Added to queue (count: 1, age: 0)
- Second detection: Re-selected (count: 2, age: 0)
- Third detection: Re-selected (count: 3, age: 0)
- High voting_score → displayed first

**Check**:
```bash
# Should see in logs:
# "Added new verse to queue: James 2:17"
# "Verse James 2:17 re-selected in queue (count: 2, age: 0, voting_score: 115)"
# "Verse James 2:17 re-selected in queue (count: 3, age: 0, voting_score: 130)"
# "✓ Verse displayed: James 2:17 (voting_score: 130, selected 3 times)"
```

### Scenario 4: Aging Mechanism
**Test**: Detect verse once, then don't mention it again

**Expected behavior**:
- Cycle 1: Added (age: 0)
- Cycle 2: Not selected → age increments (age: 1)
- Cycle 3: Not selected → age increments (age: 2)
- Cycle 4: Aged out, removed from queue (age >= 3)

**Check**:
```bash
# Should see in logs:
# "Added new verse to queue: Psalm 23:1"
# [15s later] "Aged out 1 verse(s) from queue (age >= 3)"
```

### Scenario 5: Anti-Hallucination
**This is automatic** - LLM tries to return verse not in candidates

**Expected behavior**:
- LLM returns "Mark 9:29" but it's not in candidate list
- System detects hallucination
- Falls back to top candidate
- Logs error message

**Check**:
```bash
# Should see in logs:
# "ERROR - LLM hallucinated reference 'Mark 9:29' not in candidates"
# "Falling back to top candidate: Matthew 17:21"
```

### Scenario 6: Temporal Awareness
**Test**: Repeat same topic too quickly (within 2 minutes)

Example:
1. [05:00] Discuss worry → displays Matthew 6:27
2. [05:30] Discuss worry again

**Expected behavior**:
- ContainsRelevantVerses sees previous verse at [05:00]
- Recognizes repetition
- Returns `contains_verses=False` or very low score
- No verse added to queue

**Check**:
```bash
# Should see in logs (at 05:30):
# "Reasoning: ...already covered 30 seconds ago"
# "No verse detected (edge case or low relevance)"
```

## Queue Status Monitoring

```bash
# Watch queue in real-time
tail -f logs/backend.log | grep "Queue status:"

# Example output:
# Queue (2): Matthew 6:27 (count:2, age:0, score:115), Ephesians 2:8 (count:1, age:1, score:95)
```

## Analytics Queries

```bash
# View all displayed verses for current session
sqlite3 data/sermon_analytics.sqlite "
SELECT sermon_timestamp, verse_reference, relevance_score, selection_count
FROM verse_display_log
ORDER BY id DESC
LIMIT 10
"

# Get session statistics
sqlite3 data/sermon_analytics.sqlite "
SELECT
    session_id,
    COUNT(*) as total_verses,
    AVG(relevance_score) as avg_score,
    AVG(selection_count) as avg_selections
FROM verse_display_log
GROUP BY session_id
ORDER BY session_id DESC
LIMIT 5
"

# Most popular verses across all sessions
sqlite3 data/sermon_analytics.sqlite "
SELECT verse_reference, COUNT(*) as times_displayed
FROM verse_display_log
GROUP BY verse_reference
ORDER BY times_displayed DESC
LIMIT 10
"
```

## Performance Benchmarks

### Detection Time
```bash
# Look for timing logs
tail -f logs/backend.log | grep "Step [0-9]:"

# Example expected output:
# Step 1: 0.85s
# Step 2: 0.65s
# Step 3: 0.45s
# Step 4: 0.95s
# Total: 2.90s  ← Should be <3s
```

### Queue Efficiency
```bash
# Track how many verses get displayed vs detected
tail -f logs/backend.log | grep -E "(Added new verse|Verse displayed)"

# Calculate ratio: displayed / detected
# Target: >60% of queued verses get displayed
```

## Comparison: V1 vs V2

### Run Both Versions Side-by-Side

**Terminal 1 (V1)**:
```bash
USE_PROCESSOR_V2=false ./run.sh
tail -f logs/backend.log > v1_output.log
```

**Terminal 2 (V2)**:
```bash
USE_PROCESSOR_V2=true ./run.sh
tail -f logs/backend.log > v2_output.log
```

Play same sermon audio to both, compare:
- Timing
- Verses selected
- Accuracy
- Hallucination rate

## Troubleshooting

### No verses being displayed

1. **Check queue status**:
   ```bash
   grep "Queue status:" logs/backend.log | tail -5
   ```
   - If always empty → detection failing
   - If has items but never displays → display worker issue

2. **Check detection**:
   ```bash
   grep "Detecting verses at" logs/backend.log | tail -10
   ```
   - Should run every ~10s
   - If not → transcript buffer issue

3. **Check display worker**:
   ```bash
   grep "Display worker" logs/backend.log
   ```
   - Should see "Display worker started"
   - Should see evaluations every 15s

### Verses displayed too frequently

Check cooldown:
```bash
grep "Cooldown" logs/backend.log
```

Expected: 15s minimum between displays

### Wrong verses being selected

1. **Check relevance scores**:
   ```bash
   grep "relevance_score:" logs/backend.log | tail -20
   ```

2. **Review LLM reasoning**:
   ```bash
   grep "Reasoning:" logs/backend.log | tail -10
   ```

3. **Examine search queries**:
   ```bash
   grep "Search queries:" logs/backend.log | tail -10
   ```

## Success Criteria

- ✅ Detection time <2s average
- ✅ Display time includes 15s cooldown (expected)
- ✅ Voting mechanism works (same verse gets higher score)
- ✅ Aging works (old items dropped)
- ✅ Anti-hallucination prevents invalid references
- ✅ Temporal awareness prevents repetition
- ✅ Queue never exceeds 3 items
- ✅ Analytics database populated correctly

## Known Good Test Cases

Use these phrases to test the system:

1. **Direct reference**: "Turn to Psalm 23 verse 1"
2. **Content-based**: "God's grace is sufficient for you"
3. **Repetition test**: "Faith without works is dead" (x3)
4. **Theological concept**: "We are saved by grace through faith"
5. **Narrative**: "When David faced Goliath"

Each should trigger appropriate detection and queue behavior.
