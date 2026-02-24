"""IdentifyRelevantVerses signature - extract verse references or search queries for retrieval."""
import dspy


class IdentifyRelevantVerses(dspy.Signature):
    """Extract verse references and/or search queries to retrieve relevant scripture.

    FLEXIBLE EXTRACTION: You can provide verse_references, search_queries, or BOTH simultaneously.

    === OUTPUT STRATEGY ===

    Return verse_references when:
    - Pastor explicitly cites: "Matthew 6:27 says...", "Turn to Psalm 23", "As John 3:16 tells us..."
    - Book-chapter-verse format mentioned
    - Format: ALWAYS return individual verses (e.g., "Acts 13:1; Acts 13:2; Acts 13:3")
    - NEVER return ranges (e.g., "Acts 13:1-3") - expand them into separate verses
    - Examples: "Matthew 6:27", "Psalm 23:1; Psalm 23:2", "Romans 8:28"

    Return search_queries when:
    - Biblical concepts, narratives, stories discussed
    - Theological teaching without explicit citation
    - Pastor quotes Bible but doesn't give reference
    - Use 3-5 queries with actual VERSE WORDING (not modern paraphrase)

    Return BOTH when:
    - Pastor cites a verse AND elaborates on related concepts
    - Explicit reference + you want to find related verses too
    - Example: "Matthew 6:27" (direct) + "worrying cannot add to your life" (content)

    === SEARCH QUERIES: CRITICAL RULES ===

    ✓ GOOD Queries (use biblical language from actual verses):
    - "do not be anxious about tomorrow"
    - "the Lord is my shepherd I shall not want"
    - "saved by grace through faith not by works"
    - "love your enemies pray for those who persecute"
    - "I am the way the truth and the life"
    - "help meet for him"
    - "findeth a wife findeth a good thing"

    ✗ BAD Queries (avoid these):
    - "Matthew 6:34" (that's a reference, not a query!)
    - "worry passage" (too generic/modern)
    - "Jesus talks about anxiety" (paraphrase, not Bible wording)
    - Single words like "grace" or "faith" (too broad)

    === ANECDOTAL TEACHING WITH BIBLICAL VALUE ===

    IMPORTANT: Personal stories CAN be biblical if they illustrate scriptural truth!

    EXTRACT when pastor's personal story includes:
    - Biblical terminology: "helpmate", "help meet", "fasting and prayer", "seek God's face"
    - Biblical practices: prayer for guidance, fasting for decisions, seeking God's will
    - Spiritual principles: trusting God in life decisions, divine providence, answered prayer
    - Faith testimonies: how God led/provided/answered in specific situations

    Examples of BIBLICAL anecdotes:
    ✅ "I fasted and prayed when seeking a wife" → EXTRACT (prayer/fasting principle)
    ✅ "God showed me who to marry through prayer" → EXTRACT (seeking God's guidance)
    ✅ "When I tithed faithfully, God provided" → EXTRACT (stewardship/provision)
    ✅ "I forgave my enemy and experienced peace" → EXTRACT (forgiveness principle)

    Examples of NON-BIBLICAL anecdotes:
    ❌ "My daughter graduated last week" → SKIP (just personal news)
    ❌ "We went on vacation to Florida" → SKIP (no spiritual application)
    ❌ "I like coffee in the morning" → SKIP (irrelevant detail)

    === STT TRANSCRIPTION CORRECTIONS ===

    IMPORTANT: This is Speech-to-Text (STT) data. Fix common transcription errors to match biblical wording:

    Common STT Errors → Biblical Correction:
    - "helpmate" → "help meet" (Genesis 2:18 KJV)
    - "Barnabas" (correct) vs "Barnibus" (STT error)
    - "Pharaoh" vs "Pharoah"
    - "Emmanuel" vs "Immanuel"
    - Modern phrasing → KJV/biblical phrasing when possible

    When creating search queries:
    1. Use EXACT biblical wording (KJV preferred for older terms)
    2. Correct obvious STT errors (helpmate → help meet)
    3. Map modern language → biblical language when sermon references scripture
    4. Examples:
       - Sermon: "seeking a helpmate" → Query: "help meet for him"
       - Sermon: "God will provide" → Query: "the Lord will provide"
       - Sermon: "finding a wife" → Query: "findeth a wife findeth a good thing"

    Query Strategy:
    1. Extract direct Bible quotes from sermon (if pastor quotes scripture)
    2. Use canonical biblical phrases (well-known verse wording)
    3. Correct STT errors to match biblical text (helpmate → help meet)
    4. Include unique details/imagery to narrow results
    5. 3-5 queries = good, 1-2 = too narrow, 6+ = too many

    === BIBLICAL ENTITIES ===

    Extract NAMED entities to help filter search:
    - People: Moses, David, Paul, Peter, Abraham, Mary, Pharaoh
    - Places: Egypt, Jerusalem, Babylon, Nineveh, Galilee, Bethlehem
    - Groups: Israelites, Pharisees, Sadducees, disciples, Gentiles
    - Divine: God, Jesus, Holy Spirit, Lord, Christ

    Skip generic terms: "pastor", "church", "believers", "Christians"

    === AVOID DUPLICATION ===

    DO NOT extract verses that are:
    - In previous_verses (already displayed)
    - In queued_verses (will be displayed soon)

    If context is about a queued verse, return empty strings (skip).

    === EXAMPLES OF FLEXIBILITY ===

    Scenario 1 - Direct citation only:
    Context: "Turn to Matthew 6:27"
    Output: verse_references="Matthew 6:27", search_queries="", entities="Jesus"

    Scenario 2 - Content only:
    Context: "Faith without works is dead"
    Output: verse_references="", search_queries="faith without works is dead; faith accompanied by action", entities=""

    Scenario 3 - BOTH (hybrid):
    Context: "Matthew 6:27 says we can't add hours by worrying. This anxiety is futile."
    Output: verse_references="Matthew 6:27", search_queries="worrying add hour to life; anxiety is futile", entities="Jesus"
    """

    current_time: str = dspy.InputField(
        desc="Current position in sermon as MM:SS format"
    )
    context: str = dspy.InputField(
        desc="Recent sermon transcript with [MM:SS] timestamps showing what biblical content is discussed"
    )
    previous_verses: str = dspy.InputField(
        desc="Recently displayed verses '[MM:SS] Reference' format - avoid repeating same verses"
    )
    queued_verses: str = dspy.InputField(
        desc="Verses currently in queue (not yet displayed) as 'Reference' per line - avoid extracting these"
    )

    verse_references: str = dspy.OutputField(
        desc="Semicolon-separated biblical references in format 'Book Chapter:Verse' ONLY. CRITICAL: Return individual verses (e.g., 'Acts 13:1; Acts 13:2; Acts 13:3'), NEVER ranges (e.g., 'Acts 13:1-3'). If pastor cites a range, expand it into separate verses. Leave empty if no explicit references."
    )
    search_queries: str = dspy.OutputField(
        desc="3-5 semantic search queries using actual VERSE WORDING (not references); biblical language and phrases that would appear in scripture; semicolon-separated; optimized to find relevant verses in vector database. Leave empty if not needed."
    )
    biblical_entities: str = dspy.OutputField(
        desc="Optional: Comma-separated NAMED biblical entities to help filter results: people (Moses, David, Paul), places (Egypt, Jerusalem, Nineveh), groups (Israelites, Pharisees), divine names (God, Jesus, Holy Spirit). Avoid generic terms. Empty if none."
    )


# Rich training examples
EXAMPLES = [
    # ============ DIRECT_REFERENCE: Explicit Citation ============
    dspy.Example(
        current_time="15:42",
        context="""[15:38] As Jesus says in Matthew 6:27, can any one of you by worrying add a single hour to your life?
[15:42] This is such a powerful question that cuts right to the heart of our anxiety.""",
        previous_verses="[12:15] Philippians 4:6",
        queued_verses="",
        verse_references="Matthew 6:27",
        search_queries="",
        biblical_entities="Jesus",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="22:10",
        context="""[22:05] Paul writes in Ephesians 2:8-9 that we are saved by grace through faith.
[22:10] And this not from yourselves, it is the gift of God, not by works.""",
        previous_verses="[18:30] Romans 3:23",
        queued_verses="",
        verse_references="Ephesians 2:8; Ephesians 2:9",
        search_queries="",
        biblical_entities="Paul",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="08:20",
        context="""[08:15] Turn with me to Psalm 23. The Lord is my shepherd, I shall not want.
[08:20] He makes me lie down in green pastures, he leads me beside still waters.""",
        previous_verses="",
        queued_verses="",
        verse_references="Psalm 23:1; Psalm 23:2",
        search_queries="",
        biblical_entities="The Lord",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="18:45",
        context="""[18:40] Jesus said in John 14:6, I am the way, the truth, and the life.
[18:44] No one comes to the Father except through me.
[18:47] This is an exclusive claim.""",
        previous_verses="[15:20] John 3:16",
        queued_verses="",
        verse_references="John 14:6",
        search_queries="",
        biblical_entities="Jesus",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Theological Concept ============
    dspy.Example(
        current_time="17:50",
        context="""[17:45] Brothers and sisters, we are saved by grace through faith, not by our own works.
[17:50] You can't earn God's love - it's a free gift that we receive through believing in Jesus Christ.""",
        previous_verses="[10:20] Matthew 7:24-25",
        queued_verses="",
        verse_references="",
        search_queries="saved by grace through faith not works; gift of God not by works; not from yourselves it is gift of God",
        biblical_entities="Jesus Christ",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="25:30",
        context="""[25:26] Faith without works is dead.
[25:29] If you say you believe but your life hasn't changed, if there's no fruit, no transformation,
[25:33] then examine whether you truly have faith.""",
        previous_verses="[20:10] Ephesians 2:8-9",
        queued_verses="",
        verse_references="",
        search_queries="faith without works is dead; show me your faith by your works; faith accompanied by action; dead faith",
        biblical_entities="",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="32:08",
        context="""[32:04] The Holy Spirit empowers us to do what we cannot do in our own strength.
[32:08] He is our helper, our comforter, our guide into all truth.""",
        previous_verses="[28:15] John 10:11",
        queued_verses="",
        verse_references="",
        search_queries="Holy Spirit will guide you into all truth; receive power when Holy Spirit comes; Helper Comforter Advocate; Spirit helps us in our weakness",
        biblical_entities="Holy Spirit",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="35:18",
        context="""[35:12] The resurrection changes everything. Death no longer has the final word.
[35:16] Because Christ lives, we too shall live forever with Him.
[35:20] This is our blessed hope.""",
        previous_verses="[30:30] John 14:1-3",
        queued_verses="",
        verse_references="",
        search_queries="death where is your victory; death where is your sting; Christ raised from the dead; because I live you also will live",
        biblical_entities="Christ",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Biblical Narrative ============
    dspy.Example(
        current_time="10:25",
        context="""[10:20] Think about when Moses led the Israelites out of Egypt.
[10:24] They were enslaved for 400 years, and God heard their cries.
[10:27] He sent plagues, parted the Red Sea, and brought them to freedom.""",
        previous_verses="[05:30] Psalm 23:1",
        queued_verses="",
        verse_references="",
        search_queries="Moses led Israel out of Egypt; God delivered Israel from slavery; parted the Red Sea; brought them out with mighty hand",
        biblical_entities="Moses, Israelites, Egypt, Red Sea",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="16:20",
        context="""[16:15] Now let's look at how God provided for the Israelites in the wilderness.
[16:19] Every morning, manna appeared. They couldn't store it up.
[16:23] They had to trust God day by day for their daily bread.""",
        previous_verses="[14:50] Matthew 6:27",
        queued_verses="",
        verse_references="",
        search_queries="manna in the wilderness; God provided manna from heaven; daily bread; give us this day our daily bread; bread from heaven",
        biblical_entities="Israelites",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="12:35",
        context="""[12:30] God told Jonah to go to Nineveh, but Jonah ran the opposite direction.
[12:34] He got on a ship, a storm came, and he ended up in the belly of a great fish for three days
[12:38] before God gave him a second chance.""",
        previous_verses="[08:15] Matthew 28:19",
        queued_verses="",
        verse_references="",
        search_queries="Jonah fled from the Lord; in belly of fish three days; God appointed great fish; Jonah ran from God to Tarshish",
        biblical_entities="God, Jonah, Nineveh",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Character Story ============
    dspy.Example(
        current_time="28:15",
        context="""[28:10] Remember the story of David and Goliath.
[28:14] Everyone said David was too young, too small, too inexperienced.
[28:17] But David trusted God and defeated the giant with just a sling and a stone.""",
        previous_verses="[25:40] 1 Samuel 15:22",
        queued_verses="",
        verse_references="",
        search_queries="David defeated Goliath; the battle is the Lord's; God uses weak to shame strong; David killed Philistine with sling and stone",
        biblical_entities="David, Goliath",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="20:45",
        context="""[20:40] Look at Paul's life - before he met Jesus, he was Saul the persecutor, hunting down Christians.
[20:44] Then on the road to Damascus, Jesus appeared to him in blinding light
[20:48] and transformed his entire life.""",
        previous_verses="[18:10] Acts 9:15",
        queued_verses="",
        verse_references="",
        search_queries="Saul on road to Damascus; light from heaven blinded Saul; persecutor became apostle; Saul breathed threats against disciples",
        biblical_entities="Paul, Saul, Jesus, Damascus",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="24:30",
        context="""[24:25] Abraham believed God would give him a son even though he was 100 years old and Sarah was 90.
[24:29] He believed God's promise against all logic,
[24:32] and God counted it to him as righteousness.""",
        previous_verses="[20:15] Romans 4:3",
        queued_verses="",
        verse_references="",
        search_queries="Abraham believed God counted as righteousness; faith credited as righteousness; believed against all hope; God's promise to Abraham of a son",
        biblical_entities="Abraham, Sarah, God",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Parable ============
    dspy.Example(
        current_time="19:40",
        context="""[19:35] Jesus told the parable of the prodigal son.
[19:38] The younger son took his inheritance, wasted it all, and came back home.
[19:42] The father ran to meet him, threw his arms around him, and welcomed him back.""",
        previous_verses="[15:20] Luke 15:7",
        queued_verses="",
        verse_references="",
        search_queries="parable of the prodigal son; younger son wasted inheritance; father ran to meet him; father had compassion on him; lost son was found",
        biblical_entities="Jesus, prodigal son, father",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Event ============
    dspy.Example(
        current_time="30:25",
        context="""[30:20] At Calvary, Jesus hung on the cross between two thieves.
[30:24] He cried out 'It is finished' and gave up his spirit.
[30:27] The curtain in the temple was torn in two from top to bottom.""",
        previous_verses="[27:40] John 19:30",
        queued_verses="",
        verse_references="",
        search_queries="Jesus hung on cross at Calvary; crucified between two thieves; It is finished Jesus; gave up his spirit; curtain in temple torn in two from top to bottom",
        biblical_entities="Calvary, Jesus, temple",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Teaching ============
    dspy.Example(
        current_time="14:15",
        context="""[14:10] We are called to love our enemies. Not just tolerate them, not just ignore them - actively love them.
[14:14] Pray for those who persecute you.
[14:18] Bless those who curse you.""",
        previous_verses="[10:30] Matthew 5:13-14",
        queued_verses="",
        verse_references="",
        search_queries="love your enemies and pray for those who persecute you; bless those who curse you; do good to those who hate you",
        biblical_entities="",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    dspy.Example(
        current_time="26:50",
        context="""[26:45] Brothers and sisters, worry so much about tomorrow. We stress about things we cannot control.
[26:49] But Jesus teaches us that worry adds nothing to our lives.
[26:52] It cannot change anything.""",
        previous_verses="[22:10] Philippians 4:6-7",
        queued_verses="",
        verse_references="",
        search_queries="can any one of you by worrying add single hour to your life; do not be anxious about tomorrow; worry cannot add to life",
        biblical_entities="Jesus",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ DIRECT_REFERENCE: Multiple References ============
    dspy.Example(
        current_time="33:15",
        context="""[33:10] Paul says in Romans 8:28 that all things work together for good.
[33:14] And in Philippians 4:13, I can do all things through Christ who strengthens me.
[33:18] These verses go hand in hand.""",
        previous_verses="[30:25] Jeremiah 29:11",
        queued_verses="",
        verse_references="Romans 8:28; Philippians 4:13",
        search_queries="",
        biblical_entities="Paul, Christ",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Avoid Repetition ============
    dspy.Example(
        current_time="16:45",
        context="""[16:40] God's grace is sufficient for you. His power is made perfect in our weakness.
[16:44] When we're at our lowest, that's when God's strength shines through the most.""",
        previous_verses="[14:20] 2 Corinthians 12:9\n[15:30] 2 Corinthians 12:10",
        queued_verses="",
        verse_references="",
        search_queries="my grace is sufficient for you; power made perfect in weakness; strength in weakness; when I am weak then I am strong",
        biblical_entities="God",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ HYBRID: Reference + Queries (KEY!) ============
    dspy.Example(
        current_time="21:15",
        context="""[21:10] Matthew 6:27 asks, can any one of you by worrying add a single hour to your life?
[21:14] The answer is no. Worry is futile, it changes nothing.
[21:18] Instead we should cast our anxieties on God.""",
        previous_verses="[18:40] Psalm 37:7",
        queued_verses="",
        verse_references="Matthew 6:27",  # Direct citation
        search_queries="worry is futile; cast your anxieties on God; cast all your anxiety on him",  # Related content
        biblical_entities="Jesus, God",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ HYBRID: Reference + Elaboration ============
    dspy.Example(
        current_time="29:35",
        context="""[29:30] Look at Ephesians 2:8-9 - saved by grace through faith, not by works.
[29:34] This means you can't earn salvation. It's a free gift.
[29:38] No amount of good deeds will get you into heaven.""",
        previous_verses="[25:10] Romans 3:23",
        queued_verses="",
        verse_references="Ephesians 2:8; Ephesians 2:9",
        search_queries="saved by grace through faith not works; gift of God not by works; salvation is free gift",
        biblical_entities="Paul",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Already Queued ============
    dspy.Example(
        current_time="23:50",
        context="""[23:45] We're saved by grace, not by works. This is God's free gift to us.
[23:49] You can't earn it through your own efforts.""",
        previous_verses="[20:10] Romans 3:28",
        queued_verses="Ephesians 2:8-9",  # Already in queue!
        verse_references="",
        search_queries="",
        biblical_entities="",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Already Displayed Recently ============
    dspy.Example(
        current_time="14:25",
        context="""[14:20] And again, we cannot add a single hour to our lives by worrying.
[14:24] Anxiety achieves nothing.""",
        previous_verses="[13:50] Matthew 6:27\n[14:10] Matthew 6:34",
        queued_verses="",
        verse_references="",  # Skip - same verses just shown
        search_queries="",
        biblical_entities="",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ HYBRID: Multiple Refs + Content ============
    dspy.Example(
        current_time="27:40",
        context="""[27:35] Both Romans 3 and Ephesians 2 teach justification by faith.
[27:39] Paul is consistent - we're declared righteous through faith alone, not our works.
[27:43] This is the heart of the gospel.""",
        previous_verses="[24:20] Galatians 2:16",
        queued_verses="",
        verse_references="Romans 3:28; Ephesians 2:8; Ephesians 2:9",
        search_queries="justified by faith apart from works; declared righteous through faith",
        biblical_entities="Paul",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT: Bible Quote Without Citation ============
    dspy.Example(
        current_time="19:10",
        context="""[19:05] Jesus said, I am the resurrection and the life.
[19:09] Whoever believes in me will live, even though they die.
[19:12] This is our hope in Christ.""",
        previous_verses="[16:30] 1 Corinthians 15:20",
        queued_verses="",
        verse_references="",  # No citation given
        search_queries="I am the resurrection and the life; whoever believes in me will live even though they die; believes in me shall never die",
        biblical_entities="Jesus, Christ",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ SKIP: Queue Has Multiple Related Verses ============
    dspy.Example(
        current_time="31:15",
        context="""[31:10] God is our refuge and strength in times of trouble.
[31:14] When the storms come, he is our hiding place.""",
        previous_verses="[28:20] Nahum 1:7",
        queued_verses="Psalm 46:1; Psalm 91:2; Proverbs 18:10",  # Multiple refuge verses queued
        verse_references="",
        search_queries="",
        biblical_entities="",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: STT Error Correction (helpmate → help meet) ============
    dspy.Example(
        current_time="03:46",
        context="""[03:36] When I was a young man, I fasted and prayed because I was seeking a wife.
[03:40] I said, God, who will help me? Who is my helpmate?
[03:44] I was seeking the face of God. God, who is the one you have prepared?
[03:48] When I went to Akim Oda on missions, I met these ladies.""",
        previous_verses="[01:56] Mark 2:18",
        queued_verses="",
        verse_references="",
        search_queries="help meet for him; not good that the man should be alone; findeth a wife findeth a good thing",
        biblical_entities="God",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),

    # ============ CONTENT_BASED: Marriage Teaching with Biblical Terms ============
    dspy.Example(
        current_time="12:30",
        context="""[12:25] Young men, when you're looking for a wife, don't just look at the outside.
[12:29] Proverbs tells us that a virtuous woman, her price is far above rubies.
[12:33] Seek a woman who fears the Lord, who is a helpmate for your calling.""",
        previous_verses="[10:15] Proverbs 31:10",
        queued_verses="",
        verse_references="",
        search_queries="virtuous woman price far above rubies; help meet for him; woman that feareth the Lord",
        biblical_entities="Lord",
    ).with_inputs("current_time", "context", "previous_verses", "queued_verses"),
]
