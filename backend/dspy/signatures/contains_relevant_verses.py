"""ContainsRelevantVerses signature - fast decision on whether sermon context contains retrievable biblical content."""
import dspy


class ContainsRelevantVerses(dspy.Signature):
    """Fast first-pass filter: Does this sermon segment contain biblical content worthy of verse display?

    PURPOSE: Quickly decide YES/NO to avoid expensive verse retrieval on unsuitable content.
    This runs every 10 seconds, so speed matters. Be decisive.

    === WHEN TO SKIP (contains_verses=False) ===

    1. ADMINISTRATIVE / LOGISTICS
       - Announcements, schedules, offering instructions
       - "Coffee in the fellowship hall", "Youth group Wednesday at 7pm"

    2. VAGUE / TRANSITIONAL FILLER
       - Pastor thinking out loud: "Let me think...", "Where was I?", "Hmm..."
       - No concrete theological content yet
       - Incomplete thoughts or rambling

    3. REPETITIVE CONTENT (KEY!)
       - Content about verses ALREADY in queue (check queued_verses field!)
       - Same theological point as recently displayed verses (check previous_verses timestamps)
       - If pastor keeps circling back to same topic within ~2 minutes → likely repetitive

    4. GREETING / CLOSING
       - "Good morning church!", "Let's pray", "Have a blessed week"

    === WHEN TO RETRIEVE (contains_verses=True) ===

    1. DIRECT VERSE CITATIONS (retrieval_type='direct_reference')
       - "As Matthew 6:27 says...", "Turn to Psalm 23", "John 3:16 tells us..."
       - Explicit book-chapter-verse mentioned

    2. BIBLICAL NARRATIVES (retrieval_type='content_based')
       - Stories: David and Goliath, Prodigal Son, Exodus, Pentecost
       - Character references: Moses, Paul, Abraham, Mary
       - Historical events: crucifixion, resurrection, feeding 5000

    3. THEOLOGICAL CONCEPTS (retrieval_type='content_based')
       - Grace, faith, salvation, justification, sanctification
       - Sin, redemption, atonement, covenant
       - Love, forgiveness, mercy, justice
       - Marriage, family, relationships (help meet, husband/wife roles, finding a spouse)
       - Must be substantive teaching, not just buzzwords

    4. BIBLICAL PRINCIPLES (retrieval_type='content_based')
       - "Love your enemies", "Do not worry", "Trust in the Lord"
       - Clear doctrinal teaching that maps to specific scripture
       - Ethical commands rooted in biblical text

    5. ANECDOTAL TEACHING WITH BIBLICAL VALUE (retrieval_type='content_based')
       ⚠️ IMPORTANT: Personal stories CAN be biblical if they illustrate scriptural truth!

       RETRIEVE when pastor's personal story includes:
       - Biblical terminology: "helpmate", "help meet", "fasting and prayer", "seek God's face"
       - Biblical practices: prayer for guidance, fasting for decisions, seeking God's will
       - Spiritual principles: trusting God in life decisions, divine providence, answered prayer
       - Faith testimonies: how God led/provided/answered in specific situations

       Examples of BIBLICAL anecdotes:
       ✅ "I fasted and prayed when seeking a wife" → RETRIEVE (prayer/fasting principle)
       ✅ "God showed me who to marry through prayer" → RETRIEVE (seeking God's guidance)
       ✅ "When I tithed faithfully, God provided" → RETRIEVE (stewardship/provision)
       ✅ "I forgave my enemy and experienced peace" → RETRIEVE (forgiveness principle)

       Examples of NON-BIBLICAL anecdotes:
       ❌ "My daughter graduated last week" → SKIP (just personal news)
       ❌ "We went on vacation to Florida" → SKIP (no spiritual application)
       ❌ "I like coffee in the morning" → SKIP (irrelevant detail)

       Key distinction: Does the story ILLUSTRATE a biblical truth/practice, even if informal?
       - If YES (testimony/principle) → RETRIEVE
       - If NO (just personal details) → SKIP

    === TEMPORAL AWARENESS ===

    Use timestamps to assess:
    - NEW TOPIC (recent timestamp, different from previous_verses) → Higher confidence retrieve
    - SAME TOPIC (matches recent previous_verses within ~2 min) → Lower confidence, likely skip
    - QUEUED (matches queued_verses) → ALWAYS skip (might be displayed soon)

    Example:
    - previous_verses: "[13:15] Matthew 6:27" (about worry)
    - current_time: "13:45"
    - context: discussing worry again
    - Decision: SKIP (too repetitive, only 30 seconds apart)

    === STT TRANSCRIPTION AWARENESS ===

    IMPORTANT: This is Speech-to-Text (STT) data. Recognize biblical terms even with transcription errors:

    Common Biblical Terms (may have STT errors):
    - "helpmate" or "help mate" → Biblical term (Genesis 2:18 "help meet")
    - "help meet" or "helpmeet" → Biblical concept about marriage
    - Names: Barnabas, Pharaoh, Emmanuel, Matthias, etc.
    - Biblical phrases transcribed slightly wrong are still biblical content

    When evaluating content:
    - Recognize biblical terminology even if spelled/transcribed differently
    - "helpmate" in marriage context = biblical content (retrieve!)
    - Personal stories using biblical terms = still biblical (not admin/vague)
    - Examples:
      * "seeking a helpmate" → RETRIEVE (Genesis 2:18 concept)
      * "help meet for him" → RETRIEVE (direct biblical language)
      * "finding a wife through prayer" → RETRIEVE (biblical principle)

    === EDGE CASE TIPS ===

    - When pastor quotes Bible but doesn't give reference → content_based (find it by wording)
    - When reference + explanation → direct_reference (explicit citation takes priority)
    - When unclear if biblical enough → err on side of retrieve (ranking step will filter)
    - When in doubt about queue duplication → SKIP (better safe than repetitive)
    - STT errors in biblical terms → still RETRIEVE (e.g., "helpmate" is biblical)
    """

    current_time: str = dspy.InputField(
        desc="Current position in sermon as MM:SS format (e.g., '15:23' = 15 minutes 23 seconds)"
    )
    context: str = dspy.InputField(
        desc="Recent sermon transcript with timestamp prefix [MM:SS] for each segment, showing theological development"
    )
    previous_verses: str = dspy.InputField(
        desc="Recently displayed verses with format '[MM:SS] Reference' per line (e.g., '[12:34] Matthew 6:27'); empty if none shown yet"
    )
    queued_verses: str = dspy.InputField(
        desc="Verses currently in queue (not yet displayed) as 'Reference' per line (e.g., 'Ephesians 2:8-9'); avoid detecting these again; empty if queue empty"
    )

    contains_verses: bool = dspy.OutputField(
        desc="True if context contains biblical content suitable for verse retrieval; False for admin/vague/repetitive content"
    )
    retrieval_type: str = dspy.OutputField(
        desc="Type of retrieval: 'direct_reference' (explicit verse citation), 'content_based' (biblical concepts/narratives), or 'none' (skip)"
    )


# Training examples (reasoning added automatically by ChainOfThought)
EXAMPLES = [
    # ============ SKIP: Administrative Content ============
    dspy.Example(
        current_time="05:12",
        context="""[05:10] Before we begin, just a reminder that coffee and donuts are in the fellowship hall after service.
[05:15] Also, youth group meets Wednesday at 7pm.""",
        previous_verses="",
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Vague Content ============
    dspy.Example(
        current_time="12:30",
        context="""[12:28] Let me think about this for a moment.
[12:31] Hmm, where was I going with this?
[12:34] Anyway, let me circle back to something important.""",
        previous_verses="[08:15] Matthew 5:14",
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Direct Reference ============
    dspy.Example(
        current_time="15:42",
        context="""[15:38] As Jesus says in Matthew 6:27, can any one of you by worrying add a single hour to your life?
[15:42] This is such a powerful question that cuts right to the heart of our anxiety.""",
        previous_verses="[12:15] Philippians 4:6",
        queued_verses="",
        contains_verses=True,
        retrieval_type="direct_reference"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Content-Based ============
    dspy.Example(
        current_time="17:50",
        context="""[17:45] Brothers and sisters, we are saved by grace through faith, not by our own works.
[17:50] You can't earn God's love - it's a free gift that we receive through believing in Jesus Christ.""",
        previous_verses="[10:20] Matthew 7:24-25",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Already in Queue ============
    dspy.Example(
        current_time="16:25",
        context="""[16:20] We are saved by grace, not by works.
[16:24] This is a free gift from God.""",
        previous_verses="[12:30] Romans 3:23",
        queued_verses="Ephesians 2:8-9",  # Already queued!
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Too Repetitive (Recent Display) ============
    dspy.Example(
        current_time="13:45",
        context="""[13:42] And you know what Jesus said about worry - that we shouldn't be anxious about tomorrow.
[13:46] Because each day has enough trouble of its own.""",
        previous_verses="[13:15] Matthew 6:27\n[13:30] Matthew 6:34",
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: New Angle on Same Topic ============
    dspy.Example(
        current_time="16:20",
        context="""[16:15] Now let's look at how God provided for the Israelites in the wilderness.
[16:19] Every morning, manna appeared. They couldn't store it up.
[16:23] They had to trust God day by day for their daily bread.""",
        previous_verses="[14:50] Matthew 6:27\n[15:10] Matthew 6:34",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Theological Concept ============
    dspy.Example(
        current_time="25:30",
        context="""[25:26] Faith without works is dead.
[25:29] If you say you believe but your life hasn't changed, if there's no fruit,
[25:33] then examine whether you truly have faith.""",
        previous_verses="[20:10] Ephesians 2:8-9",
        queued_verses="Romans 4:3",
        contains_verses=True,
        retrieval_type="content_based"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Greeting/Opening ============
    dspy.Example(
        current_time="01:05",
        context="""[01:00] Good morning church! It's so good to see everyone here today.
[01:05] Let's all stand together as we open in prayer.""",
        previous_verses="",
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Biblical Narrative ============
    dspy.Example(
        current_time="18:15",
        context="""[18:10] Think about David facing Goliath. Everyone else was terrified.
[18:14] But David said, who is this uncircumcised Philistine that he should defy the armies of the living God?
[18:18] David had faith that God would deliver him.""",
        previous_verses="[15:20] Psalm 27:1",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Same Concept Already Queued ============
    dspy.Example(
        current_time="22:40",
        context="""[22:35] Remember, we are justified by faith, not by works.
[22:39] It's God's grace that saves us, through our faith in Jesus.""",
        previous_verses="[18:10] Romans 3:28",
        queued_verses="Ephesians 2:8-9\nGalatians 2:16",  # Both about grace/faith
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Direct Quote Without Citation ============
    dspy.Example(
        current_time="14:25",
        context="""[14:20] Jesus said, I am the way, the truth, and the life.
[14:24] No one comes to the Father except through me.
[14:27] This is an exclusive claim about salvation.""",
        previous_verses="[10:15] John 3:16",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"  # No citation given, but clear Bible quote
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Closing Benediction ============
    dspy.Example(
        current_time="35:50",
        context="""[35:45] Let's close in prayer. Father, we thank you for your word today.
[35:50] Send us out with your blessing. In Jesus' name, Amen.""",
        previous_verses="[32:10] Philippians 4:13\n[34:20] Romans 8:28",
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Multiple References Mentioned ============
    dspy.Example(
        current_time="20:30",
        context="""[20:25] Look at both Ephesians 2 and Romans 3.
[20:29] Both Paul passages emphasize that we're saved by grace, not works.
[20:33] This is consistent throughout Paul's teaching.""",
        previous_verses="[18:40] Galatians 3:11",
        queued_verses="",
        contains_verses=True,
        retrieval_type="direct_reference"  # Multiple refs mentioned
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Too Recent Repetition (30 seconds) ============
    dspy.Example(
        current_time="10:45",
        context="""[10:42] And again, Jesus tells us not to worry about tomorrow.
[10:45] Each day has enough trouble of its own.""",
        previous_verses="[10:15] Matthew 6:34",  # Just 30 seconds ago!
        queued_verses="",
        contains_verses=False,
        retrieval_type="none"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Biblical Principle Teaching ============
    dspy.Example(
        current_time="27:15",
        context="""[27:10] We are called to love our enemies. Not tolerate them, not ignore them - love them.
[27:14] Pray for those who persecute you. Do good to those who hate you.
[27:18] This is radical, counter-cultural love.""",
        previous_verses="[22:30] Romans 12:9-10",
        queued_verses="1 John 4:7",
        contains_verses=True,
        retrieval_type="content_based"
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Marriage & Relationships (Biblical Concept) ============
    dspy.Example(
        current_time="32:45",
        context="""[32:40] When I was a young man, I fasted and prayed about who I should marry.
[32:44] I asked God to show me the woman He had prepared as a help meet for me.
[32:48] God created Eve as a help meet for Adam. This is His design for marriage.""",
        previous_verses="[28:10] Ephesians 5:22",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"  # "help meet" is biblical (Genesis 2:18, 20)
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Prayer for Guidance (Biblical Practice) ============
    dspy.Example(
        current_time="18:50",
        context="""[18:45] The church at Antioch fasted and prayed, seeking God's direction.
[18:49] As they ministered to the Lord, the Holy Spirit spoke to them.
[18:53] When we need divine guidance, we must fast and pray like they did.""",
        previous_verses="[15:20] Proverbs 3:5-6",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"  # Biblical narrative about seeking God's will
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: Personal Story with Biblical Application ============
    dspy.Example(
        current_time="25:30",
        context="""[25:25] A young man once asked me, how do I know which woman to marry?
[25:29] I told him what I did - fast and pray. Seek God's will, not just physical attraction.
[25:33] Proverbs says he who finds a wife finds a good thing and obtains favor from the Lord.""",
        previous_verses="[22:15] 1 Corinthians 7:2",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"  # References Proverbs teaching about marriage
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ RETRIEVE: STT Error - "helpmate" (recognize as biblical despite transcription) ============
    dspy.Example(
        current_time="03:46",
        context="""[03:36] When I was a young man, I fasted and prayed because I was seeking a wife.
[03:40] I said, God, who will help me? Who is my helpmate?
[03:44] I was seeking the face of God. God, who is the one you have prepared?
[03:48] When I went to Akim Oda on missions, I met these ladies.""",
        previous_verses="[01:56] Mark 2:18",
        queued_verses="",
        contains_verses=True,
        retrieval_type="content_based"  # "helpmate" is STT error for "help meet" (Genesis 2:18) - still biblical!
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),
]
