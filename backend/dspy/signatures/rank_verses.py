"""RankVerses signature - select best verse from candidates."""
import dspy


class RankVerses(dspy.Signature):
    """Select the scripture verse that most powerfully reinforces the sermon's theological message.

    TASK: Rank candidate verses by how well they align with the sermon context, then return the best one.

    === ANECDOTAL TEACHING WITH BIBLICAL VALUE ===

    IMPORTANT: Personal stories CAN be biblical if they illustrate scriptural truth!

    When scoring anecdotal content:
    - **Score HIGH (70+)** if story demonstrates biblical practice/principle (prayer, fasting, seeking God, faith testimony)
    - **Score LOW (<50)** if story is purely personal without spiritual application
    - Key question: Does this illustrate a scriptural truth the congregation can apply?

    Examples:
    ✅ HIGH SCORE: "I fasted and prayed when seeking a wife" → Match with Genesis 2:18/Proverbs 18:22 (70-80)
    ✅ HIGH SCORE: "God provided when I tithed faithfully" → Match with Malachi 3:10 (75-85)
    ❌ LOW SCORE: "My daughter graduated last week" → No spiritual application (10-20)

    === SCORING GUIDELINES ===

    **90-100: PERFECT MATCH** 🎯
    - Verse wording directly echoes sermon language (same key phrases/metaphors)
    - Addresses the EXACT theological point, not just general topic
    - Creates "aha!" moment - congregation immediately sees connection
    - Example: Pastor says "worry adds nothing to life" → Matthew 6:27 "can worrying add a single hour?"

    **70-89: STRONG CONCEPTUAL ALIGNMENT** ✓
    - Verse clearly supports the theological argument
    - May not use exact wording but concept is unmistakable
    - Would make sense to congregation with brief explanation
    - Example: Pastor discusses God's provision → Psalm 23 "I shall not want"

    **50-69: MODERATE RELEVANCE** ~
    - Verse relates to general topic area
    - Requires significant explanation to connect
    - Useful but not ideal for live display
    - Example: Pastor discusses faith → verse about Abraham's specific test

    **0-49: WEAK/TANGENTIAL CONNECTION** ✗
    - Verse only loosely connected or too generic
    - Could apply to many different sermons
    - Congregation would be confused by the connection
    - Example: Pastor discusses prayer → Genesis 1:1 creation verse

    === SELECTION CRITERIA ===

    **PRIORITIZE:**
    1. **Direct Language Match** - Same words/phrases as sermon
    2. **Theological Precision** - Exact point being taught, not just topic
    3. **Self-Contained** - Verse makes sense without explanation
    4. **Memorable** - Short, punchy, quotable (prefer 1-2 verses over 5+)
    5. **Authoritative** - Jesus' words, clear doctrinal statements (Paul, Peter)
    6. **Consecutive Verses** - When multiple verses from same passage appear (Acts 13:1, Acts 13:2, Acts 13:3), consider each individually based on which specific verse best matches the sermon point

    **AVOID:**
    1. **Generic Verses** - "God is love" could fit 100 sermons
    2. **Requires Context** - Needs prior verses to understand
    3. **Tangential** - Shares topic but different point
    4. **Too Long** - 5+ verses hard to display and absorb
    5. **Name-Only Match** - Just mentions same person but different topic

    === ANTI-HALLUCINATION RULES ===

    ⚠️ CRITICAL: You MUST select from the numbered candidates list.
    - DO NOT invent references not in the list
    - DO NOT modify references (keep exact format)
    - If all candidates are weak, pick the best available (don't return "none")
    - If multiple equally good, prefer shorter/more famous verses

    === HOW TO ANALYZE ===

    1. **Check temporal context** - Review previous_verses with timestamps
       - Has similar verse been shown recently (within ~2 min)?
       - Is this a repetitive topic?
    2. **Read sermon context** - What specific point is pastor making?
    3. **Extract core theme** - Distill to 3-8 word concept
    4. **Read each candidate** - Does verse wording echo sermon?
    5. **Score each candidate** - Use 0-100 scale rigorously
       - Lower score if too similar to recent verses
    6. **Return best match** - Exact reference from list + score

    === EXAMPLES OF THEME EXTRACTION ===

    Context: "Worry adds nothing. We stress about things beyond our control but it changes nothing."
    Theme: "futility of worry, trusting God"

    Context: "You can't earn God's love through good deeds. It's a free gift."
    Theme: "unconditional grace, salvation by faith"

    Context: "When everything falls apart, God is our shelter, our hiding place."
    Theme: "God as refuge during trials"

    Remember: The best verse creates an instant connection - congregation hears it and thinks "That's exactly what the pastor is saying!"
    """

    current_time: str = dspy.InputField(
        desc="Current position in sermon as MM:SS format (e.g., '15:23') - provides temporal context for scoring"
    )
    context: str = dspy.InputField(
        desc="Consecutive 60-second window of sermon transcript with [MM:SS] timestamps showing the theological argument or narrative being developed by the pastor"
    )
    previous_verses: str = dspy.InputField(
        desc="Recently displayed verses with format '[MM:SS] Reference' per line (e.g., '[12:34] Matthew 6:27') - avoid selecting verses too similar to recent ones or on same topic within ~2 minutes"
    )
    candidates: str = dspy.InputField(
        desc="Semantically retrieved candidate verses formatted as numbered list with full reference (book chapter:verse) and complete verse text"
    )

    verse_reference: str = dspy.OutputField(
        desc="CRITICAL: You MUST select from the numbered candidates list above. Return the EXACT reference shown in the candidates (e.g., 'Matthew 6:27', 'Ephesians 2:8-9'). DO NOT invent or hallucinate references not in the list. If none are suitable, return the best available option."
    )
    relevance_score: int = dspy.OutputField(
        desc="Numerical score 0-100 indicating theological alignment strength, where 90+ means near-perfect thematic match with direct language echoes, 70-89 means strong conceptual alignment, 50-69 means moderate relevance, below 50 means weak/tangential connection. IMPORTANT: Lower score if verse is too similar to recently displayed verses."
    )


# Rich training examples
EXAMPLES = [
    # ============ PERFECT MATCH: Direct Thematic Alignment ============
    dspy.Example(
        current_time="15:42",
        context="None of it changed anything. This is what Jesus tells us - that our worry and anxiety don't add a single hour to our lives. We spend so much energy on things beyond our control.",
        previous_verses="[12:15] Philippians 4:6\n[14:20] Psalm 27:1",  # Different topics from 3+ min ago

        candidates="""1. Matthew 6:27
   "Can any one of you by worrying add a single hour to your life?"

2. Philippians 4:6-7
   "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus."

3. 1 Peter 5:7
   "Cast all your anxiety on him because he cares for you."

4. Psalm 55:22
   "Cast your cares on the LORD and he will sustain you; he will never let the righteous be shaken."

5. Proverbs 12:25
   "Anxiety weighs down the heart, but a kind word cheers it up.\"""",
        verse_reference="Matthew 6:27",
        relevance_score=95
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ PERFECT MATCH: Grace vs Works ============
    dspy.Example(
        current_time="22:35",
        context="God's love isn't something we earn. You can't work hard enough, be good enough, or pray long enough to deserve it. It's a free gift.",
        previous_verses="[18:10] Romans 3:23\n[20:45] John 3:16",

        candidates="""1. Ephesians 2:8-9
   "For it is by grace you have been saved, through faith—and this is not from yourselves, it is the gift of God— not by works, so that no one can boast."

2. Romans 3:23-24
   "For all have sinned and fall short of the glory of God, and all are justified freely by his grace through the redemption that came by Christ Jesus."

3. Titus 3:5
   "He saved us, not because of righteous things we had done, but because of his mercy."

4. Romans 6:23
   "For the wages of sin is death, but the gift of God is eternal life in Christ Jesus our Lord."

5. John 3:16
   "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.\"""",
        verse_reference="Ephesians 2:8-9",
        relevance_score=98
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ STRONG MATCH: Refuge During Trials ============
    dspy.Example(
        current_time="28:15",
        context="When the storm hits your life, and it will hit, where do you turn? God is our shelter, our hiding place when everything falls apart.",
        previous_verses="[24:30] Proverbs 3:5-6\n[26:40] Isaiah 40:31",

        candidates="""1. Psalm 46:1
   "God is our refuge and strength, an ever-present help in trouble."

2. Proverbs 18:10
   "The name of the LORD is a fortified tower; the righteous run to it and are safe."

3. Nahum 1:7
   "The LORD is good, a refuge in times of trouble. He cares for those who trust in him."

4. Psalm 91:1-2
   "Whoever dwells in the shelter of the Most High will rest in the shadow of the Almighty. I will say of the LORD, 'He is my refuge and my fortress, my God, in whom I trust.'"

5. 2 Samuel 22:3
   "My God is my rock, in whom I take refuge, my shield and the horn of my salvation. He is my stronghold, my refuge and my savior."\"""",
        verse_reference="Psalm 46:1",
        relevance_score=97
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ CHOOSING BETWEEN STRONG OPTIONS ============
    dspy.Example(
        current_time="00:00",
        context="Jesus is the Good Shepherd who laid down His life for us. He knows each of us by name and leads us beside still waters.",
        previous_verses="",

        candidates="""1. John 10:11
   "I am the good shepherd. The good shepherd lays down his life for the sheep."

2. Psalm 23:1-2
   "The LORD is my shepherd, I lack nothing. He makes me lie down in green pastures, he leads me beside quiet waters."

3. John 10:14
   "I am the good shepherd; I know my sheep and my sheep know me."

4. Ezekiel 34:15
   "I myself will tend my sheep and have them lie down, declares the Sovereign LORD."

5. 1 Peter 2:25
   "For you were like sheep going astray, but now you have returned to the Shepherd and Overseer of your souls.\"""",
        verse_reference="John 10:11",
        relevance_score=96
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ WEAK MATCH: Low Relevance ============
    dspy.Example(
        current_time="00:00",
        context="We need to be better stewards of our finances. God calls us to manage money wisely and give generously to those in need.",
        previous_verses="",

        candidates="""1. Genesis 1:1
   "In the beginning God created the heavens and the earth."

2. Revelation 21:4
   "He will wipe every tear from their eyes. There will be no more death or mourning or crying or pain."

3. Psalm 23:1
   "The LORD is my shepherd, I lack nothing."

4. Matthew 5:14
   "You are the light of the world. A town built on a hill cannot be hidden."

5. Philippians 4:19
   "And my God will meet all your needs according to the riches of his glory in Christ Jesus.\"""",
        verse_reference="Philippians 4:19",
        relevance_score=45
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ STRONG MATCH: Resurrection Hope ============
    dspy.Example(
        current_time="00:00",
        context="The resurrection changes everything. Death no longer has the final word. Because Christ lives, we too shall live forever with Him.",
        previous_verses="",

        candidates="""1. 1 Corinthians 15:55-57
   "Where, O death, is your victory? Where, O death, is your sting? The sting of death is sin, and the power of sin is the law. But thanks be to God! He gives us the victory through our Lord Jesus Christ."

2. John 11:25-26
   "Jesus said to her, 'I am the resurrection and the life. The one who believes in me will live, even though they die; and whoever lives by believing in me will never die.'"

3. Romans 6:9
   "For we know that since Christ was raised from the dead, he cannot die again; death no longer has mastery over him."

4. 1 Corinthians 15:20
   "But Christ has indeed been raised from the dead, the firstfruits of those who have fallen asleep."

5. 1 Thessalonians 4:14
   "For we believe that Jesus died and rose again, and so we believe that God will bring with Jesus those who have fallen asleep in him.\"""",
        verse_reference="1 Corinthians 15:55-57",
        relevance_score=94
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ STRONG MATCH: Faith and Works ============
    dspy.Example(
        current_time="00:00",
        context="Faith without works is dead. True belief transforms how we live. If your faith hasn't changed your life, examine whether you truly believe.",
        previous_verses="",

        candidates="""1. James 2:17
   "In the same way, faith by itself, if it is not accompanied by action, is dead."

2. James 2:26
   "As the body without the spirit is dead, so faith without deeds is dead."

3. Matthew 7:20
   "Thus, by their fruit you will recognize them."

4. Galatians 5:6
   "For in Christ Jesus neither circumcision nor uncircumcision has any value. The only thing that counts is faith expressing itself through love."

5. 1 John 3:18
   "Dear children, let us not love with words or speech but with actions and in truth.\"""",
        verse_reference="James 2:17",
        relevance_score=99
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ GOOD MATCH: Love Your Enemies ============
    dspy.Example(
        current_time="00:00",
        context="We are called to love our enemies. Not just tolerate them, not just ignore them - actively love them. Pray for those who persecute you.",
        previous_verses="",

        candidates="""1. Matthew 5:44
   "But I tell you, love your enemies and pray for those who persecute you."

2. Luke 6:27-28
   "But to you who are listening I say: Love your enemies, do good to those who hate you, bless those who curse you, pray for those who mistreat you."

3. Romans 12:20
   "On the contrary: 'If your enemy is hungry, feed him; if he is thirsty, give him something to drink. In doing this, you will heap burning coals on his head.'"

4. Proverbs 25:21
   "If your enemy is hungry, give him food to eat; if he is thirsty, give him water to drink."

5. Matthew 5:39
   "But I tell you, do not resist an evil person. If anyone slaps you on the right cheek, turn to them the other cheek also.\"""",
        verse_reference="Matthew 5:44",
        relevance_score=98
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ STRONG MATCH: Holy Spirit Empowerment ============
    dspy.Example(
        current_time="00:00",
        context="The Holy Spirit empowers us to do what we cannot do in our own strength. He is our helper, our comforter, our guide into all truth.",
        previous_verses="",

        candidates="""1. John 14:26
   "But the Advocate, the Holy Spirit, whom the Father will send in my name, will teach you all things and will remind you of everything I have said to you."

2. Acts 1:8
   "But you will receive power when the Holy Spirit comes on you; and you will be my witnesses in Jerusalem, and in all Judea and Samaria, and to the ends of the earth."

3. John 16:13
   "But when he, the Spirit of truth, comes, he will guide you into all the truth. He will not speak on his own; he will speak only what he hears, and he will tell you what is yet to come."

4. Romans 8:26
   "In the same way, the Spirit helps us in our weakness. We do not know what we ought to pray for, but the Spirit himself intercedes for us through wordless groans."

5. Galatians 5:22-23
   "But the fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness, gentleness and self-control. Against such things there is no law.\"""",
        verse_reference="Acts 1:8",
        relevance_score=92
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ MODERATE MATCH: Choosing More Specific Over General ============
    dspy.Example(
        current_time="25:40",
        context="Prayer isn't about getting what we want. It's about aligning our will with God's will. Sometimes the answer is no, and that's still an answer.",
        previous_verses="[20:10] Romans 8:28\n[23:15] James 5:16",

        candidates="""1. 1 John 5:14-15
   "This is the confidence we have in approaching God: that if we ask anything according to his will, he hears us. And if we know that he hears us—whatever we ask—we know that we have what we asked of him."

2. Matthew 6:10
   "Your kingdom come, your will be done, on earth as it is in heaven."

3. Matthew 26:39
   "Going a little farther, he fell with his face to the ground and prayed, 'My Father, if it is possible, may this cup be taken from me. Yet not as I will, but as you will.'"

4. James 4:3
   "When you ask, you do not receive, because you ask with wrong motives, that you may spend what you get on your pleasures."

5. Psalm 37:4
   "Take delight in the LORD, and he will give you the desires of your heart.\"""",
        verse_reference="1 John 5:14-15",
        relevance_score=89
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ REPETITION PENALTY: Similar Verse Recently Shown ============
    dspy.Example(
        current_time="16:25",
        context="And once again, let me emphasize - worrying achieves nothing. It doesn't add anything to your life. Anxiety is futile.",
        previous_verses="[15:50] Matthew 6:27\n[16:10] Matthew 6:34",  # Worry verses JUST shown!

        candidates="""1. Philippians 4:6-7
   "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus."

2. 1 Peter 5:7
   "Cast all your anxiety on him because he cares for you."

3. Matthew 6:25
   "Therefore I tell you, do not worry about your life, what you will eat or drink; or about your body, what you will wear. Is not life more than food, and the body more than clothing?"

4. Psalm 55:22
   "Cast your cares on the LORD and he will sustain you; he will never let the righteous be shaken."

5. Luke 12:25
   "Who of you by worrying can add a single hour to your life?\"""",
        verse_reference="1 Peter 5:7",  # Different angle - casting anxiety
        relevance_score=75  # LOWER because worry topic was JUST covered 35 sec ago
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ GOOD MATCH DESPITE RECENT SIMILAR TOPIC: New Angle ============
    dspy.Example(
        current_time="18:40",
        context="Now let's talk about HOW to deal with this worry. The solution is to cast your anxieties on God, because He cares for you. Don't just stop worrying - actively give it to Him.",
        previous_verses="[15:50] Matthew 6:27\n[16:25] 1 Peter 5:7",  # Recent but different angle

        candidates="""1. Philippians 4:6-7
   "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus."

2. Psalm 55:22
   "Cast your cares on the LORD and he will sustain you; he will never let the righteous be shaken."

3. Matthew 11:28-30
   "Come to me, all you who are weary and burdened, and I will give you rest. Take my yoke upon you and learn from me, for I am gentle and humble in heart, and you will find rest for your souls. For my yoke is easy and my burden is light."

4. Proverbs 3:5-6
   "Trust in the LORD with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight."

5. Isaiah 26:3
   "You will keep in perfect peace those whose minds are steadfast, because they trust in you.\"""",
        verse_reference="Philippians 4:6-7",  # Specific HOW (prayer + thanksgiving)
        relevance_score=88  # HIGH because it's a NEW ANGLE on worry (practical solution vs futility)
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ CONSECUTIVE VERSES: Select Best Individual Verse ============
    dspy.Example(
        current_time="18:30",
        context="""[18:25] In the church at Antioch, the Holy Spirit said, "Separate me Barnabas and Saul for the work whereunto I have called them."
[18:29] God had a specific mission for Paul and Barnabas. He set them apart for his purposes.
[18:33] When they had fasted and prayed, they laid their hands on them and sent them away.""",
        previous_verses="[15:10] Romans 12:1",

        candidates="""1. Acts 13:1
   "Now there were in the church that was at Antioch certain prophets and teachers; as Barnabas, and Simeon that was called Niger, and Lucius of Cyrene, and Manaen, which had been brought up with Herod the tetrarch, and Saul."

2. Acts 13:2
   "As they ministered to the Lord, and fasted, the Holy Ghost said, Separate me Barnabas and Saul for the work whereunto I have called them."

3. Acts 13:3
   "And when they had fasted and prayed, and laid their hands on them, they sent them away."

4. Romans 1:1
   "Paul, a servant of Christ Jesus, called to be an apostle and set apart for the gospel of God."

5. Galatians 1:15
   "But when God, who set me apart from my mother's womb and called me by his grace, was pleased to reveal his Son in me so that I might preach him among the Gentiles."\"""",
        verse_reference="Acts 13:2",  # Best match - contains exact quoted phrase about Holy Spirit's call
        relevance_score=97  # PERFECT - sermon directly quotes this verse's language
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ REJECT WEAK MATCH: Personal Story Without Theological Content ============
    dspy.Example(
        current_time="03:46",
        context="""[03:36] When I was a young man, I went to fast and pray because I was seeking a wife.
[03:40] I said, God, who will help me? Who is my helpmate?
[03:44] I was seeking the face of God. God, who is the one you have prepared?
[03:48] When I went to Akim Oda on missions, I met these ladies.""",
        previous_verses="[01:56] Mark 2:18\n[02:11] Acts 1:23",

        candidates="""1. Job 23:6
   "Will he plead against me with his great power? No; but he would put strength in me."

2. Psalms 55:22
   "Cast thy burden upon the LORD, and he shall sustain thee: he shall never suffer the righteous to be moved."

3. Psalms 138:7
   "Though I walk in the midst of trouble, thou wilt revive me: thou shalt stretch forth thine hand against the wrath of mine enemies, and thy right hand shall save me."

4. Genesis 2:18
   "And the LORD God said, It is not good that the man should be alone; I will make him an help meet for him."

5. Proverbs 18:22
   "Whoso findeth a wife findeth a good thing, and obtaineth favour of the LORD.\"""",
        verse_reference="Proverbs 18:22",  # Only candidate with direct marriage relevance
        relevance_score=35  # LOW - personal anecdote, not theological teaching
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ REJECT VERY WEAK MATCH: Name-Only Connection ============
    dspy.Example(
        current_time="02:05",
        context="""[01:56] The apostles fasted and prayed before sending people on assignment.
[02:00] They ministered to the Lord and fasted, seeking divine guidance.
[02:04] This is what we see throughout Acts - prayer and fasting for direction.""",
        previous_verses="[00:17] Mark 9:29\n[00:53] Acts 13:2",

        candidates="""1. Acts 4:36
   "And Joses, who by the apostles was surnamed Barnabas, (which is, being interpreted, The son of consolation,) a Levite, and of the country of Cyprus."

2. Acts 1:23
   "And they appointed two, Joseph called Barsabas, who was surnamed Justus, and Matthias."

3. Mark 2:18
   "And the disciples of John and of the Pharisees used to fast: and they come and say unto him, Why do the disciples of John and of the Pharisees fast, but thy disciples fast not?"

4. Acts 14:23
   "And when they had ordained them elders in every church, and had prayed with fasting, they commended them to the Lord, on whom they believed."

5. Matthew 17:21
   "Howbeit this kind goeth not out but by prayer and fasting.\"""",
        verse_reference="Acts 14:23",  # Directly mentions prayer with fasting in appointing context
        relevance_score=82  # STRONG but not perfect (different context than Acts 13)
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),

    # ============ REJECT GENERIC MATCH: Too Broad/Vague ============
    dspy.Example(
        current_time="03:20",
        context="""[03:10] When we go through difficult times, we need to remember that God is with us.
[03:15] He gives us strength. He upholds us.
[03:19] We don't walk alone through our trials.""",
        previous_verses="[01:40] Psalm 23:4\n[02:50] Isaiah 41:10",

        candidates="""1. Psalm 46:1
   "God is our refuge and strength, a very present help in trouble."

2. Philippians 4:13
   "I can do all things through Christ which strengtheneth me."

3. Isaiah 40:31
   "But they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles; they shall run, and not be weary; and they shall walk, and not faint."

4. Psalm 28:7
   "The LORD is my strength and my shield; my heart trusted in him, and I am helped: therefore my heart greatly rejoiceth; and with my song will I praise him."

5. 2 Corinthians 12:9
   "And he said unto me, My grace is sufficient for thee: for my strength is made perfect in weakness. Most gladly therefore will I rather glory in my infirmities, that the power of Christ may rest upon me.\"""",
        verse_reference="2 Corinthians 12:9",  # Specific theology about strength in weakness
        relevance_score=55  # MODERATE - too generic, similar to recent verses
    ).with_inputs("current_time", "context", "previous_verses", "candidates"),
]
