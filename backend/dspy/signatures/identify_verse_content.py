"""IdentifyVerseContent signature - identify biblical content for direct verse retrieval."""
import dspy


class IdentifyVerseContent(dspy.Signature):
    """Identify what biblical content, entities, or verses are being referenced in the sermon.

    This signature focuses on WHAT is being discussed rather than extracting abstract themes:
    - Direct verse quotes/mentions (e.g., "As Matthew 6:27 says...")
    - Biblical narratives (e.g., "When Israel left Egypt...")
    - Character stories (e.g., "David facing Goliath...")
    - Theological concepts that map to specific verses

    The goal is to identify concrete biblical references that can be searched directly.
    """

    context: str = dspy.InputField(desc="Consecutive 60-second window of sermon transcript")
    previous_verses: str = dspy.InputField(desc="Previously shown verse references to avoid repetition, one per line (e.g., 'Matthew 6:27'); empty if none shown yet")

    content_type: str = dspy.OutputField(desc="Type of biblical content: 'direct_reference' (explicit verse citation or direct quote), 'narrative' (biblical story/event), 'character_story' (person's story), 'theological_concept' (abstract teaching/doctrine), or 'none' (no biblical content)")
    biblical_entities: str = dspy.OutputField(desc="Comma-separated list of biblical entities: people (Moses, David, Paul, prodigal son, father), places (Egypt, Jerusalem, Calvary, Nineveh), groups (Israelites, Pharisees, thieves), objects/locations (temple, Red Sea, ark); include divine names (God, Jesus, Holy Spirit, The Lord); do NOT include book names unless they are the subject being discussed; empty if none")
    search_queries: str = dspy.OutputField(desc="1-3 semantic search queries to find verses in vector database; use actual verse WORDING not references (e.g., 'worrying cannot add single hour to life' not 'Matthew 6:27'); use biblical language and phrases; include thematic/conceptual queries; separated by semicolons; empty if no biblical content; avoid topics already covered by previous verses")


# Rich training examples
EXAMPLES = [
    # ============ DIRECT VERSE REFERENCE ============
    dspy.Example(
        context="As Jesus says in Matthew 6:27, 'Can any one of you by worrying add a single hour to your life?' This is such a powerful question that cuts right to the heart of our anxiety.",
        previous_verses="",
        content_type="direct_reference",
        biblical_entities="Jesus",
        search_queries="can any one of you by worrying add single hour to your life; do not be anxious about tomorrow",
    ).with_inputs("context", "previous_verses"),

    # ============ BIBLICAL NARRATIVE: EXODUS ============
    dspy.Example(
        context="Think about when Moses led the Israelites out of Egypt. They were enslaved for 400 years, and God heard their cries. He sent plagues, parted the Red Sea, and brought them to freedom.",
        previous_verses="",
        content_type="narrative",
        biblical_entities="Moses, Israelites, Egypt, Red Sea",
        search_queries="Moses led Israel out of Egypt; God delivered Israel from slavery; parted the Red Sea",
    ).with_inputs("context", "previous_verses"),

    # ============ CHARACTER STORY: DAVID AND GOLIATH ============
    dspy.Example(
        context="Remember the story of David and Goliath. Everyone said David was too young, too small, too inexperienced. But David trusted God and defeated the giant with just a sling and a stone.",
        previous_verses="",
        content_type="character_story",
        biblical_entities="David, Goliath",
        search_queries="David defeated Goliath; the battle is the Lord's; God uses weak to shame strong",
    ).with_inputs("context", "previous_verses"),

    # ============ THEOLOGICAL CONCEPT: GRACE ============
    dspy.Example(
        context="Brothers and sisters, we are saved by grace through faith, not by our own works. You can't earn God's love - it's a free gift that we receive through believing in Jesus Christ.",
        previous_verses="",
        content_type="theological_concept",
        biblical_entities="Jesus Christ",
        search_queries="saved by grace through faith not works; salvation is gift of God; not by works lest anyone should boast",
    ).with_inputs("context", "previous_verses"),

    # ============ DIRECT REFERENCE: EPHESIANS (Author mentioned) ============
    dspy.Example(
        context="Paul writes in Ephesians 2:8-9 that we are saved by grace through faith, and this not from yourselves, it is the gift of God, not by works.",
        previous_verses="",
        content_type="direct_reference",
        biblical_entities="Paul",
        search_queries="saved by grace through faith; gift of God not by works; not from yourselves",
    ).with_inputs("context", "previous_verses"),

    # ============ NARRATIVE: PRODIGAL SON ============
    dspy.Example(
        context="Jesus told the parable of the prodigal son - the younger son who took his inheritance, wasted it all, and came back home. The father ran to meet him, threw his arms around him, and welcomed him back.",
        previous_verses="",
        content_type="narrative",
        biblical_entities="Jesus, prodigal son, father",
        search_queries="parable of the prodigal son; younger son wasted inheritance; father ran to meet him; father had compassion on him",
    ).with_inputs("context", "previous_verses"),

    # ============ CHARACTER STORY: PAUL'S CONVERSION ============
    dspy.Example(
        context="Look at Paul's life - before he met Jesus, he was Saul the persecutor, hunting down Christians. Then on the road to Damascus, Jesus appeared to him in blinding light and transformed his entire life.",
        previous_verses="",
        content_type="character_story",
        biblical_entities="Paul, Saul, Jesus, Damascus",
        search_queries="Saul on road to Damascus; light from heaven; persecutor became apostle",
    ).with_inputs("context", "previous_verses"),

    # ============ THEOLOGICAL CONCEPT: FAITH WITHOUT WORKS ============
    dspy.Example(
        context="Faith without works is dead. If you say you believe but your life hasn't changed, if there's no fruit, no transformation, then examine whether you truly have faith.",
        previous_verses="",
        content_type="theological_concept",
        biblical_entities="",
        search_queries="faith without works is dead; show me your faith by your works; faith accompanied by action",
    ).with_inputs("context", "previous_verses"),

    # ============ NARRATIVE: JONAH ============
    dspy.Example(
        context="God told Jonah to go to Nineveh, but Jonah ran the opposite direction. He got on a ship, a storm came, and he ended up in the belly of a great fish for three days before God gave him a second chance.",
        previous_verses="",
        content_type="narrative",
        biblical_entities="God, Jonah, Nineveh",
        search_queries="Jonah fled from the Lord; in belly of fish three days; God appointed great fish; Jonah ran from God",
    ).with_inputs("context", "previous_verses"),

    # ============ CHARACTER STORY: ABRAHAM'S FAITH ============
    dspy.Example(
        context="Abraham believed God would give him a son even though he was 100 years old and Sarah was 90. He believed God's promise against all logic, and God counted it to him as righteousness.",
        previous_verses="",
        content_type="character_story",
        biblical_entities="Abraham, Sarah, God",
        search_queries="Abraham believed God counted as righteousness; faith credited as righteousness; believed against all hope; God's promise to Abraham",
    ).with_inputs("context", "previous_verses"),

    # ============ DIRECT REFERENCE: PSALM 23 ============
    dspy.Example(
        context="We all know Psalm 23 - 'The Lord is my shepherd, I shall not want. He makes me lie down in green pastures, he leads me beside still waters.' This psalm brings such comfort.",
        previous_verses="",
        content_type="direct_reference",
        biblical_entities="The Lord",
        search_queries="Psalm 23; The Lord is my shepherd I shall not want; lie down in green pastures; leads me beside still waters",
    ).with_inputs("context", "previous_verses"),

    # ============ NARRATIVE: CRUCIFIXION ============
    dspy.Example(
        context="At Calvary, Jesus hung on the cross between two thieves. He cried out 'It is finished' and gave up his spirit. The curtain in the temple was torn in two from top to bottom.",
        previous_verses="",
        content_type="narrative",
        biblical_entities="Calvary, Jesus, thieves, temple",
        search_queries="Jesus hung on the cross at Calvary; Jesus between two thieves; It is finished Jesus; gave up his spirit; curtain in the temple torn in two from top to bottom",
    ).with_inputs("context", "previous_verses"),

    # ============ THEOLOGICAL CONCEPT: HOLY SPIRIT POWER ============
    dspy.Example(
        context="The Holy Spirit gives us power to do what we cannot do on our own. He is our helper, our comforter, the one who guides us into all truth and convicts us of sin.",
        previous_verses="",
        content_type="theological_concept",
        biblical_entities="Holy Spirit",
        search_queries="receive power when Holy Spirit comes; Spirit will guide you into all truth; Helper Comforter Advocate",
    ).with_inputs("context", "previous_verses"),

    # ============ NO BIBLICAL CONTENT ============
    dspy.Example(
        context="Don't forget that coffee and donuts are in the fellowship hall after service. Also, youth group meets on Wednesday at 7pm in the basement.",
        previous_verses="",
        content_type="none",
        biblical_entities="",
        search_queries="",
    ).with_inputs("context", "previous_verses"),

    # ============ CHARACTER STORY: PETER WALKS ON WATER ============
    dspy.Example(
        context="Peter stepped out of the boat and walked on water toward Jesus. But when he saw the wind and waves, he became afraid and started to sink. Jesus reached out and caught him, saying 'You of little faith, why did you doubt?'",
        previous_verses="",
        content_type="character_story",
        biblical_entities="Peter, Jesus",
        search_queries="Peter walked on water; when he saw wind became afraid; you of little faith why did you doubt",
    ).with_inputs("context", "previous_verses"),

    # ============ WITH PREVIOUS VERSES: AVOID REPETITION ============
    dspy.Example(
        context="And you know what Jesus said about worry - that we shouldn't be anxious about tomorrow, because each day has enough trouble of its own. Trust God for today.",
        previous_verses="Matthew 6:27\nMatthew 6:34\nPhilippians 4:6",
        content_type="theological_concept",
        biblical_entities="Jesus",
        search_queries="trust God for today; sufficient for day is own trouble; do not worry about tomorrow",
    ).with_inputs("context", "previous_verses"),

    # ============ WITH PREVIOUS VERSES: NEW ANGLE ============
    dspy.Example(
        context="Now let's look at how God provided for the Israelites in the wilderness. Every morning, manna appeared. They couldn't store it up - they had to trust God day by day for their daily bread.",
        previous_verses="Matthew 6:27\nMatthew 6:34",
        content_type="narrative",
        biblical_entities="Israelites",
        search_queries="manna in wilderness; daily bread; God provided manna every morning",
    ).with_inputs("context", "previous_verses"),

    # ============ WITH PREVIOUS VERSES: DIFFERENT TOPIC ============
    dspy.Example(
        context="God's grace is sufficient for you. His power is made perfect in our weakness. When we're at our lowest, that's when God's strength shines through the most.",
        previous_verses="Ephesians 2:8-9\nRomans 3:23-24",
        content_type="theological_concept",
        biblical_entities="God",
        search_queries="my grace is sufficient for you; power made perfect in weakness; strength in weakness",
    ).with_inputs("context", "previous_verses"),

    # ============ WITH PREVIOUS VERSES: SAME THEME DIFFERENT VERSE ============
    dspy.Example(
        context="The resurrection changes everything. Paul says that if Christ has not been raised, our faith is futile. But Christ has been raised from the dead, the firstfruits of those who have fallen asleep.",
        previous_verses="1 Corinthians 15:55-57\nJohn 11:25-26",
        content_type="theological_concept",
        biblical_entities="Paul, Christ",
        search_queries="if Christ not raised faith is futile; Christ raised from dead; firstfruits of those who have fallen asleep",
    ).with_inputs("context", "previous_verses"),
]
