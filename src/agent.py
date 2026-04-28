"""
MusicAgent — agentic workflow with observable reasoning chain.

STRETCH FEATURE — Agentic Enhancement:
  Every step of the pipeline emits a ReasoningStep with:
    - name, input summary, decision made, alternatives considered, confidence
  The full chain is returned in AgentResult.reasoning_chain and displayed in the UI.

  A PLAN step now runs first, deciding which retrieval strategy to use:
    - simple   : song-catalog RAG only
    - context  : context-augmented RAG (two data sources)
    - broad    : search all songs (fallback for very vague queries)

Pipeline:
  PLAN → PARSE → RETRIEVE → SCORE → VALIDATE (retry up to 3×) → EXPLAIN
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rag_engine import RAGEngine
from recommender import recommend_songs
from logger_config import setup_logger

logger = setup_logger("agent")

# ---------------------------------------------------------------------------
# Keyword tables for NLU
# ---------------------------------------------------------------------------

_MOOD_KEYWORDS: Dict[str, List[str]] = {
    "happy":        ["happy", "upbeat", "fun", "cheerful", "joyful", "positive", "celebrat", "bright"],
    "chill":        ["chill", "relax", "calm", "easy", "mellow", "smooth", "cozy", "lounge"],
    "intense":      ["intense", "pump", "hype", "powerful", "strong", "fire", "hard"],
    "focused":      ["focus", "study", "concentrate", "work", "productive", "deep"],
    "moody":        ["moody", "dark", "brooding", "gloomy", "introspective", "complex"],
    "peaceful":     ["peaceful", "serene", "tranquil", "meditat", "sleep", "quiet", "wind down"],
    "euphoric":     ["euphoric", "dance", "party", "club", "rave", "festival", "hype"],
    "melancholic":  ["melanchol", "sad", "blue", "down", "emotional", "cry", "nostalg"],
    "aggressive":   ["aggressive", "angry", "rage", "brutal"],
    "laid-back":    ["laid-back", "laid back", "easy going", "island", "reggae", "breezy"],
    "relaxed":      ["relaxed", "jazz", "slow", "sunday", "afternoon", "coffee"],
}

_GENRE_KEYWORDS: Dict[str, List[str]] = {
    "pop":        ["pop"],
    "rock":       ["rock"],
    "hip-hop":    ["hip hop", "hip-hop", "rap", "trap"],
    "jazz":       ["jazz"],
    "classical":  ["classical", "orchestra", "piano", "violin"],
    "metal":      ["metal", "heavy metal"],
    "lofi":       ["lofi", "lo-fi", "lo fi"],
    "ambient":    ["ambient", "atmospheric", "drone"],
    "synthwave":  ["synthwave", "synth", "retrowave", "80s"],
    "indie pop":  ["indie", "indie pop"],
    "country":    ["country"],
    "electronic": ["electronic", "edm", "techno", "house"],
    "blues":      ["blues"],
    "reggae":     ["reggae"],
    "folk":       ["folk", "acoustic singer"],
}

_HIGH_ENERGY_CUES = [
    "workout", "gym", "run", "sprint", "hype", "pump", "dance", "party",
    "intense", "high energy", "energetic", "exercise", "cardio",
    "hip hop", "hip-hop", "rap", "trap",
    "heavy", "metal", "hard rock", "rock",
]
_LOW_ENERGY_CUES = [
    "sleep", "nap", "relax", "calm", "chill", "study", "focus",
    "meditat", "peaceful", "lofi", "ambient", "quiet", "wind down",
]

# Context cues that trigger context-augmented retrieval (two data sources)
_CONTEXT_CUES = [
    "studying", "study", "gym", "workout", "sleep", "party", "road trip",
    "driving", "morning", "evening", "night", "coding", "focus", "relax",
    "chill", "dance", "meditat",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReasoningStep:
    """Observable intermediate step in the agent's decision chain."""
    step: str            # e.g. "PLAN", "PARSE", "RETRIEVE"
    decision: str        # the choice made
    rationale: str       # why
    alternatives: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ParsedQuery:
    raw_query: str
    mood: Optional[str] = None
    genre: Optional[str] = None
    energy: float = 0.5
    confidence: float = 0.5
    context_keywords: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    query: ParsedQuery
    rag_candidates: List[Tuple[Dict, float]]
    recommendations: List[Tuple[Dict, float, str]]
    validation_passed: bool
    iterations: int
    explanation: str
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)
    matched_contexts: List[Dict] = field(default_factory=list)
    retrieval_strategy: str = "simple"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class MusicAgent:
    """Multi-step music recommendation agent with observable reasoning chain."""

    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine
        logger.info("MusicAgent initialized (%d songs, context source: %s)",
                    len(rag_engine.songs),
                    "enabled" if rag_engine.context_docs else "disabled")

    # ------------------------------------------------------------------
    # Step 0 — Plan
    # ------------------------------------------------------------------

    def _plan(self, query: str, chain: List[ReasoningStep]) -> str:
        """Decide retrieval strategy before doing any work."""
        lower = query.lower()
        ctx_hits = sum(1 for cue in _CONTEXT_CUES if cue in lower)
        has_context_source = bool(self.rag.context_docs)

        if has_context_source and ctx_hits >= 2:
            strategy = "context"
            rationale = (
                f"Query contains {ctx_hits} context cue(s) and context documents are loaded. "
                "Using two-source retrieval to bridge vocabulary gaps."
            )
            alternatives = ["simple (fewer cues detected)", "broad (no cues at all)"]
        elif len(query.split()) <= 3 and not any(w in lower for w in _GENRE_KEYWORDS):
            strategy = "broad"
            rationale = "Very short query with no genre signal; searching full catalog."
            alternatives = ["simple", "context"]
        else:
            strategy = "simple"
            rationale = "Standard query — using song-catalog semantic search."
            alternatives = ["context (would need more context cues)", "broad"]

        chain.append(ReasoningStep(
            step="PLAN",
            decision=f"Use '{strategy}' retrieval strategy",
            rationale=rationale,
            alternatives=alternatives,
            confidence=0.9 if ctx_hits >= 2 else 0.7,
        ))
        logger.info("PLAN: strategy=%s (ctx_hits=%d)", strategy, ctx_hits)
        return strategy

    # ------------------------------------------------------------------
    # Step 1 — Parse
    # ------------------------------------------------------------------

    def parse_query(self, text: str, chain: Optional[List[ReasoningStep]] = None) -> ParsedQuery:
        lower = text.lower()

        mood = None
        best_count = 0
        for m, keywords in _MOOD_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in lower)
            if count > best_count:
                best_count = count
                mood = m

        genre = None
        for g, keywords in _GENRE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                genre = g
                break

        high_count = sum(1 for kw in _HIGH_ENERGY_CUES if kw in lower)
        low_count  = sum(1 for kw in _LOW_ENERGY_CUES  if kw in lower)
        if high_count > low_count:
            energy = 0.85
        elif low_count > high_count:
            energy = 0.2
        else:
            energy = 0.5

        context_keywords = [
            w for w in ["study", "workout", "sleep", "party", "drive", "meditat", "relax", "focus"]
            if w in lower
        ]

        confidence = min(1.0,
            0.3
            + (0.25 if mood else 0)
            + (0.25 if genre else 0)
            + (0.1  if energy != 0.5 else 0)
            + (0.1  if context_keywords else 0)
        )

        parsed = ParsedQuery(
            raw_query=text,
            mood=mood, genre=genre, energy=energy,
            confidence=confidence, context_keywords=context_keywords,
        )

        if chain is not None:
            chain.append(ReasoningStep(
                step="PARSE",
                decision=f"mood={mood or 'any'}, genre={genre or 'any'}, energy={energy:.2f}",
                rationale=(
                    f"Detected {best_count} mood keyword(s) for '{mood}'. "
                    f"Genre from keyword match: {genre or 'none'}. "
                    f"Energy cues: high={high_count}, low={low_count}."
                ),
                alternatives=[
                    f"mood could also be: {[m for m in _MOOD_KEYWORDS if m != mood][:2]}",
                    "energy=0.5 (default) if cues cancel out",
                ],
                confidence=confidence,
            ))
        logger.info("PARSE: mood=%s genre=%s energy=%.2f conf=%.2f",
                    mood, genre, energy, confidence)
        return parsed

    # ------------------------------------------------------------------
    # Step 2 — Retrieve
    # ------------------------------------------------------------------

    def _retrieve(
        self, query: str, strategy: str, chain: List[ReasoningStep]
    ) -> Tuple[List[Tuple[Dict, float]], List[Dict]]:
        top_k = min(len(self.rag.songs), 15)
        matched_contexts: List[Dict] = []

        if strategy == "context" and self.rag.context_docs:
            results, matched_contexts = self.rag.retrieve_with_context(query, top_k=top_k)
            ctx_names = [c["name"] for c in matched_contexts[:2]]
            chain.append(ReasoningStep(
                step="RETRIEVE",
                decision=f"Context-augmented search; {len(results)} candidates",
                rationale=(
                    f"Two data sources queried: song catalog + music_contexts.json. "
                    f"Matching context docs: {ctx_names or 'none'}. "
                    "Tagged songs received a similarity boost."
                ),
                alternatives=["simple search (no context boost)"],
                confidence=0.9,
            ))
        elif strategy == "broad":
            results = [(s, 0.0) for s in self.rag.songs]
            chain.append(ReasoningStep(
                step="RETRIEVE",
                decision="Broad search — full catalog",
                rationale="Query too short/vague for semantic search; scoring alone will rank.",
                alternatives=["simple", "context"],
                confidence=0.5,
            ))
        else:
            results = self.rag.retrieve(query, top_k=top_k)
            chain.append(ReasoningStep(
                step="RETRIEVE",
                decision=f"Song-catalog semantic search; {len(results)} candidates",
                rationale=f"Top result: '{results[0][0]['title']}' (sim={results[0][1]:.3f}).",
                alternatives=["context-augmented (would boost tagged songs)"],
                confidence=0.85,
            ))

        return results, matched_contexts

    # ------------------------------------------------------------------
    # Step 3 — Score  (logged externally)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Step 4 — Validate
    # ------------------------------------------------------------------

    def _validate(
        self,
        recommendations: List[Tuple[Dict, float, str]],
        parsed: ParsedQuery,
        chain: List[ReasoningStep],
    ) -> bool:
        if not recommendations:
            chain.append(ReasoningStep("VALIDATE", "FAIL", "No recommendations returned.", confidence=0.0))
            return False

        top_songs = [r[0] for r in recommendations[:3]]

        if parsed.mood:
            mood_hits = sum(1 for s in top_songs if s.get("mood", "").lower() == parsed.mood.lower())
            if mood_hits == 0:
                chain.append(ReasoningStep(
                    step="VALIDATE",
                    decision="FAIL — mood mismatch",
                    rationale=f"Expected mood '{parsed.mood}' absent from top 3; got {[s['mood'] for s in top_songs]}.",
                    alternatives=["relax genre constraint", "relax mood constraint"],
                    confidence=0.3,
                ))
                return False

        avg_energy = sum(float(s.get("energy", 0.5)) for s in top_songs) / len(top_songs)
        if parsed.energy > 0.7 and avg_energy < 0.4:
            chain.append(ReasoningStep(
                step="VALIDATE",
                decision="FAIL — energy too low",
                rationale=f"Wanted high energy ({parsed.energy:.2f}) but avg={avg_energy:.2f}.",
                confidence=0.3,
            ))
            return False
        if parsed.energy < 0.3 and avg_energy > 0.7:
            chain.append(ReasoningStep(
                step="VALIDATE",
                decision="FAIL — energy too high",
                rationale=f"Wanted low energy ({parsed.energy:.2f}) but avg={avg_energy:.2f}.",
                confidence=0.3,
            ))
            return False

        chain.append(ReasoningStep(
            step="VALIDATE",
            decision="PASS",
            rationale=f"Mood present in top 3. Average energy {avg_energy:.2f} matches target {parsed.energy:.2f}.",
            confidence=0.95,
        ))
        return True

    # ------------------------------------------------------------------
    # Step 5 — Explain
    # ------------------------------------------------------------------

    def _build_explanation(
        self,
        parsed: ParsedQuery,
        rag_candidates: List[Tuple[Dict, float]],
        recommendations: List[Tuple[Dict, float, str]],
        iterations: int,
        validation_passed: bool,
        strategy: str,
        matched_contexts: List[Dict],
    ) -> str:
        rag_titles   = [s["title"] for s, _ in rag_candidates[:3]]
        final_titles = [r[0]["title"] for r in recommendations[:3]]
        ctx_names    = [c["name"] for c in matched_contexts[:2]]

        lines = [
            f'Query: "{parsed.raw_query}"',
            "",
            f"Step 0 — PLAN: chose '{strategy}' retrieval strategy",
            f"Step 1 — PARSE: mood={parsed.mood or 'any'}, genre={parsed.genre or 'any'}, "
            f"energy={parsed.energy:.2f}, confidence={parsed.confidence:.0%}",
        ]
        if parsed.context_keywords:
            lines.append(f"         context cues: {', '.join(parsed.context_keywords)}")

        if strategy == "context" and ctx_names:
            lines.append(
                f"Step 2 — RETRIEVE: context-augmented search (2 sources); "
                f"matched contexts: {', '.join(ctx_names)}"
            )
        else:
            lines.append(f"Step 2 — RETRIEVE: '{strategy}' search; closest: {', '.join(rag_titles)}")

        lines += [
            f"Step 3 — SCORE: content-based re-ranking of {len(rag_candidates)} candidates",
            f"Step 4 — VALIDATE: {'passed' if validation_passed else 'relaxed after'} "
            f"{iterations} iteration(s)",
            f"Step 5 — RESULT: {', '.join(final_titles)}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(
        self, query: str, k: int = 5, max_iterations: int = 3, profile=None
    ) -> AgentResult:
        logger.info("Agent pipeline — query='%s'", query)
        if not query or not query.strip():
            logger.warning("Empty query; using default")
            query = "chill music"

        chain: List[ReasoningStep] = []

        # Step 0 — Plan
        strategy = self._plan(query, chain)

        # Step 1 — Parse
        parsed = self.parse_query(query, chain)

        # Step 2 — Retrieve
        rag_candidates, matched_contexts = self._retrieve(query, strategy, chain)

        user_prefs: Dict = {
            "mood":   parsed.mood or "chill",
            "genre":  parsed.genre,
            "energy": parsed.energy,
        }
        candidate_songs = [s for s, _ in rag_candidates]

        recommendations: List[Tuple[Dict, float, str]] = []
        iterations = 0
        validation_passed = False

        for i in range(max_iterations):
            iterations = i + 1

            # Widen candidate pool if genre missing from RAG results
            if user_prefs.get("genre"):
                genre_present = any(
                    s.get("genre", "").lower() == user_prefs["genre"].lower()
                    for s in candidate_songs
                )
                if not genre_present:
                    logger.info("Retry %d: genre '%s' absent — widening pool", i + 1, user_prefs["genre"])
                    candidate_songs = self.rag.songs

            # Step 3 — Score
            recommendations = recommend_songs(user_prefs, candidate_songs, k=k, profile=profile)
            chain.append(ReasoningStep(
                step="SCORE",
                decision=f"Top result: '{recommendations[0][0]['title']}' (score={recommendations[0][1]:.2f})",
                rationale=f"Scored {len(candidate_songs)} candidates; profile={'custom' if profile else 'balanced'}.",
                confidence=0.9,
            ))

            # Step 4 — Validate
            if self._validate(recommendations, parsed, chain):
                validation_passed = True
                break

            # Adjust for retry
            if i == 0:
                user_prefs = {**user_prefs, "genre": None}
            elif i == 1:
                user_prefs = {**user_prefs, "mood": None}
                candidate_songs = self.rag.songs

        # Step 5 — Explain
        explanation = self._build_explanation(
            parsed, rag_candidates, recommendations, iterations, validation_passed, strategy, matched_contexts
        )
        chain.append(ReasoningStep(
            step="EXPLAIN",
            decision="Explanation generated",
            rationale="Full reasoning chain logged and returned.",
            confidence=1.0,
        ))

        logger.info("Agent done — %d iter(s), valid=%s, strategy=%s",
                    iterations, validation_passed, strategy)
        return AgentResult(
            query=parsed,
            rag_candidates=rag_candidates,
            recommendations=recommendations,
            validation_passed=validation_passed,
            iterations=iterations,
            explanation=explanation,
            reasoning_chain=chain,
            matched_contexts=matched_contexts,
            retrieval_strategy=strategy,
        )
