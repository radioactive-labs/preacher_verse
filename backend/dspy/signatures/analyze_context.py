"""AnalyzeContext signature - edge case detection and theme extraction."""
import dspy


class AnalyzeContext(dspy.Signature):
    """Identify whether sermon context is suitable for verse display and extract the core biblical theme.

    Unsuitable contexts include:
    - Administrative announcements (schedules, logistics, offering instructions)
    - Vague/ambiguous language lacking concrete theological content

    Suitable contexts present theological ideas that can be reinforced with scripture.
    Sermons naturally unfold over time - even partial narratives or developing thoughts that mention biblical concepts are suitable for verse reinforcement.
    Teaching about scripture or biblical narratives is ALWAYS suitable for verse reinforcement.
    """

    context: str = dspy.InputField(desc="Consecutive 60-second window of spoken sermon transcript capturing recent theological development")

    should_skip: bool = dspy.OutputField(desc="Whether context is unsuitable for verse display due to edge cases")
    skip_reason: str = dspy.OutputField(desc="Specific edge case category if unsuitable: admin_content (logistics/schedules), ambiguous (vague pronouns/incomplete ideas), or 'none' if suitable")
    theme: str = dspy.OutputField(desc="Core biblical concept or theological truth expressed in 3-8 words, optimized for semantic search against scripture (e.g., 'futility of worry trusting God', 'unconditional grace salvation by faith'); empty if context unsuitable")
    search_query: str = dspy.OutputField(desc="Biblical search query using scriptural language and concepts to match Bible verses (e.g., 'God provides for our needs during trials', 'love your enemies and pray for those who persecute you', 'faith without works is dead'); use biblical terminology and phrasing that would naturally appear in scripture; empty if context unsuitable")
    reasoning: str = dspy.OutputField(desc="Detailed justification explaining either why context is unsuitable (citing specific edge case indicators) or what theological theme was identified and why it merits verse display")


# Rich training examples
EXAMPLES = [
    # ============ EDGE CASE: Administrative Content ============
    dspy.Example(
        context="Before we begin, just a reminder that coffee and donuts are in the fellowship hall after service. Also, youth group meets Wednesday at 7pm.",
        should_skip=True,
        skip_reason="admin_content",
        theme="",
        search_query="",
        reasoning="Church logistics and schedules - not sermon content"
    ).with_inputs("context"),

    dspy.Example(
        context="Don't forget to sign up for the church retreat next month. Forms are in the back. We need volunteers for parking lot duty this Sunday.",
        should_skip=True,
        skip_reason="admin_content",
        theme="",
        search_query="",
        reasoning="Administrative announcements about retreat and volunteers - no theological content"
    ).with_inputs("context"),

    dspy.Example(
        context="Please silence your phones. Our offering today will go toward the building fund. Ushers, please come forward.",
        should_skip=True,
        skip_reason="admin_content",
        theme="",
        search_query="",
        reasoning="Service logistics (phones, offering, ushers) - procedural instructions"
    ).with_inputs("context"),

    dspy.Example(
        context="If you're visiting today, welcome! We have guest cards in the pews. After service, join us for refreshments in the lobby.",
        should_skip=True,
        skip_reason="admin_content",
        theme="",
        search_query="",
        reasoning="Visitor welcome and logistics - administrative hospitality instructions"
    ).with_inputs("context"),

    # ============ EDGE CASE: Ambiguous/Vague Content ============
    dspy.Example(
        context="Let me think about this for a moment. Hmm, where was I going with this? Anyway, let me circle back to something important.",
        should_skip=True,
        skip_reason="ambiguous",
        theme="",
        search_query="",
        reasoning="Pastor thinking aloud - no clear theological theme yet"
    ).with_inputs("context"),

    dspy.Example(
        context="You know what I mean? This is something we all struggle with. It's just really important to understand this concept.",
        should_skip=True,
        skip_reason="ambiguous",
        theme="",
        search_query="",
        reasoning="Vague references without specific theological content - unclear what concept is discussed"
    ).with_inputs("context"),

    dspy.Example(
        context="There's something I want to talk about today. It's been on my heart lately. Just bear with me as I gather my thoughts.",
        should_skip=True,
        skip_reason="ambiguous",
        theme="",
        search_query="",
        reasoning="Non-specific introduction - topic not yet revealed"
    ).with_inputs("context"),

    dspy.Example(
        context="This reminds me of a thing. You probably know what I'm talking about. We've all been there, right?",
        should_skip=True,
        skip_reason="ambiguous",
        theme="",
        search_query="",
        reasoning="Vague pronouns ('a thing', 'what I'm talking about') - no concrete theological content"
    ).with_inputs("context"),

    # ============ VALID: Clear Themes ============
    dspy.Example(
        context="Brothers and sisters, we worry so much about tomorrow. We stress about things we cannot control. But Jesus teaches us that worry adds nothing to our lives.",
        should_skip=False,
        skip_reason="none",
        theme="futility of worry trusting God",
        search_query="do not be anxious about tomorrow for each day has enough trouble",
        reasoning="Clear theological theme about worry's futility and trusting God instead"
    ).with_inputs("context"),

    dspy.Example(
        context="God's love is not based on our performance. We can't earn it through good works. It's freely given, unconditional, and eternal.",
        should_skip=False,
        skip_reason="none",
        theme="unconditional grace salvation by faith",
        search_query="by grace you have been saved through faith not of works",
        reasoning="Distinct theme about grace vs works, salvation as free gift"
    ).with_inputs("context"),

    dspy.Example(
        context="When trials come, and they will come, we have a choice. We can run from God or run to God. He is our refuge in times of trouble.",
        should_skip=False,
        skip_reason="none",
        theme="God as refuge during trials",
        search_query="God is our refuge and strength a very present help in trouble",
        reasoning="Theme of finding refuge in God during hardship - actionable spiritual truth"
    ).with_inputs("context"),

    dspy.Example(
        context="Jesus is the Good Shepherd. He laid down His life for the sheep. He knows each of us by name and will never abandon us.",
        should_skip=False,
        skip_reason="none",
        theme="Jesus Good Shepherd sacrificial love",
        search_query="the good shepherd lays down his life for the sheep",
        reasoning="Clear Christological theme - Jesus as shepherd who sacrifices for his flock"
    ).with_inputs("context"),

    dspy.Example(
        context="We are called to love our enemies. Not just tolerate them, not just ignore them - actively love them. Pray for those who persecute you.",
        should_skip=False,
        skip_reason="none",
        theme="loving enemies forgiveness",
        search_query="love your enemies and pray for those who persecute you",
        reasoning="Ethical teaching theme - radical love extending even to enemies"
    ).with_inputs("context"),

    dspy.Example(
        context="The resurrection changes everything. Death no longer has the final word. Because He lives, we too shall live.",
        should_skip=False,
        skip_reason="none",
        theme="resurrection hope victory over death",
        search_query="because I live you also will live death has no more dominion",
        reasoning="Core gospel theme - resurrection's transformative power and hope"
    ).with_inputs("context"),

    dspy.Example(
        context="Faith without works is dead. True belief transforms how we live. If your faith hasn't changed your life, examine whether you truly believe.",
        should_skip=False,
        skip_reason="none",
        theme="faith demonstrated through works",
        search_query="faith without works is dead show me your faith by your works",
        reasoning="Theme linking belief and action - genuine faith produces fruit"
    ).with_inputs("context"),

    dspy.Example(
        context="The Holy Spirit empowers us to do what we cannot do in our own strength. He is our helper, our comforter, our guide into all truth.",
        should_skip=False,
        skip_reason="none",
        theme="Holy Spirit empowerment guidance",
        search_query="the Spirit will guide you into all truth and give you power",
        reasoning="Pneumatological theme - Spirit's role in believer's life"
    ).with_inputs("context"),
]
