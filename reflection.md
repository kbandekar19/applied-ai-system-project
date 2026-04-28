# Reflection and Ethics: Thinking Critically About VibeMatcher AI

---

## Limitations and Biases in the System

**Catalog bias is the most significant limitation.** VibeMatcher AI operates on 18 songs, and the distribution is uneven: lofi has 3 songs, while classical, metal, jazz, and blues each have only 1. This means a user who loves classical music will always get the same top result, no matter how their query is phrased. In a real recommendation system, this would translate to underrepresentation — certain genres, artists, and cultural styles get far less visibility than others, not because they are less valid, but because the dataset reflects the curator's taste and familiarity.

**The keyword parser has a Western, English-language bias.** The mood and genre keywords built into the parser are drawn from English music vocabulary. A user who writes "musica para estudiar" (Spanish for "studying music") or describes music using non-Western genre terms would get poor intent detection — their query would fall back to semantic similarity alone. The system was not designed with multilingual users in mind.

**Energy and valence are treated as universal.** The scoring formula assumes that "high energy" and "positivity" (valence) are good or bad depending on context in the same way for every user. But mood and energy preferences are culturally shaped. Music that sounds "intense" to one listener sounds "powerful" to another. The system has no way to learn from feedback or adjust to individual users — it treats all users as equivalent.

**The parser cannot understand negation or comparison.** Queries like "something that's *not* too intense" or "more like jazz but less mellow" are parsed on their positive keywords — "intense," "jazz," "mellow" — and can give the opposite of what was asked. This is a real failure mode for natural language interfaces.

---

## Could This AI Be Misused?

A music recommender seems low-stakes, but the design patterns here scale into higher-risk contexts.

**Filter bubbles.** Even at 18 songs, I noticed the system repeatedly returning the same 3–5 songs for any given mood. A system like this at scale would narrow what music people discover — not through malice, but through optimization. If a recommender is rewarded for giving people what they already like, it will stop showing them anything new. The result is a listener whose taste appears broad but has actually been quietly funneled into a narrow slice of what exists.

**Proxy discrimination.** Music preference is correlated — imperfectly but measurably — with demographic factors like age, ethnicity, and geography. A recommender trained on behavioral data (not this one, but a scaled-up version) could learn to surface different music to different user groups in ways that reinforce cultural separation or limit certain artists' reach. This is not a hypothetical; similar dynamics have been documented in content recommendation on major platforms.

**Confidence without calibration.** The system assigns a confidence score to every query, but that score measures how many keywords were detected — not how likely the recommendations are to actually satisfy the user. A high-confidence score accompanying wrong results could mislead a user into trusting the system more than it deserves.

**Prevention in this project:** The transparency panel in the Streamlit UI is the primary safeguard. By showing exactly what intent was parsed, which songs were retrieved by RAG, and why each recommendation scored the way it did, the system invites scrutiny rather than asking for blind trust. This does not prevent all misuse, but it makes the reasoning auditable — a user can see when the system misunderstood them.

---

## What Surprised Me During Reliability Testing

The most surprising finding was that the agentic retry loop — which took significant effort to design — was never triggered once across all 12 evaluation tests. Every query passed self-validation on the first iteration. I had expected it to be a meaningful guardrail for ambiguous queries, but in practice, the combination of RAG retrieval and content-based scoring produced aligned results without needing correction.

This revealed something important about safety mechanisms: **their value is not always visible in their activation rate.** Knowing there was a fallback made me less cautious about edge cases elsewhere in the system, because I knew the validator would catch serious misalignments. The retry loop's existence shaped the design of the whole pipeline even though it never fired.

The second surprise was how a single keyword collision caused two test failures — both invisible in the code and only detectable through real output. The word `"heavy"` was in the aggressive mood keyword list (reasonable: "heavy music" often implies aggression). But when a user typed "heavy rock music," the parser gave Midnight Bars (hip-hop/aggressive) a mood bonus that outscored Storm Runner (rock/intense) — a completely wrong result that was internally consistent with the rules I had written. No code review would have caught this. Running real queries against expected outputs is what found it.

---

## Collaboration with AI During This Project

I used Claude (Anthropic's AI assistant) as a collaborator throughout — for architectural design, code generation, debugging, and writing.

**One instance where AI collaboration was genuinely helpful:**
When I described the project goals, Claude suggested combining RAG with content-based filtering in a specific way: use RAG to produce a *smaller candidate pool* (top 15 semantically relevant songs), then run the scoring formula only on those candidates rather than the full catalog. I had initially thought of RAG and content-based scoring as alternatives to each other. Claude reframed them as complementary — RAG's job is to narrow the search space so scoring operates on already-relevant songs, not to replace scoring. This made the architecture cleaner and the results noticeably more accurate. The query "chill lofi for studying" returned `Library Rain (lofi/chill)` as the #1 result, which is exactly right — RAG had already filtered out irrelevant genres before the scorer ran.

**One instance where AI collaboration was flawed:**
Claude initially placed the keyword `"heavy"` in the aggressive mood keyword list, reasoning that "heavy music" is commonly associated with aggression. This was plausible logic but produced wrong results in practice: "heavy rock music" was parsed as aggressive mood, and Midnight Bars (hip-hop/aggressive) received a mood bonus that pushed it above Storm Runner (the actual rock song). The recommendation was internally consistent with the code but useless from a user's perspective. The bug was not caught during code generation — it only surfaced when I ran the automated test battery and read the actual output. This was a good reminder that AI-generated code can be logically coherent and factually wrong simultaneously. The fix was straightforward once the cause was found, but finding the cause required testing real queries, not trusting the code.

---

## Summary

Building VibeMatcher AI taught me that responsible AI development is mostly about being honest about what your system cannot do. Every design decision involved a trade-off: keyword NLU is interpretable but brittle; RAG is powerful but opaque without the transparency panel; confidence scoring sounds rigorous but only measures keyword detection. The places where the system is weakest — negation, multilingual queries, small catalog diversity — are also the places where a user would be most likely to be misled by a confident-looking output.

The most important habit I am taking from this project: test against real outputs, not just code logic. The bugs that mattered were not visible in the source. They only appeared when the system was asked real questions and gave real answers.
