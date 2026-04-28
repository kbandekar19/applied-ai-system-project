"""
VibeMatcher AI — Reliability & Testing Evaluation  (STRETCH: Test Harness)

Runs a battery of tests measuring:
  - Relevance     : top result matches stated mood / genre
  - Consistency   : same query → same top result (deterministic)
  - Edge cases    : empty input, unknown genre, conflicting prefs
  - RAG quality   : context-augmented vs. basic retrieval comparison
  - Profiles      : different ScoringProfiles produce measurably different results

Usage (from project root):
    python -m evaluate.evaluate
"""

import sys
import os
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in [_ROOT, os.path.join(_ROOT, "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from recommender import load_songs
from rag_engine import RAGEngine, load_context_documents
from agent import MusicAgent
from profiles import get_profile
from logger_config import setup_logger

logger = setup_logger("evaluate")


# ---------------------------------------------------------------------------
# Test case definition
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name: str
    query: str
    expect_mood: Optional[str] = None
    expect_genre: Optional[str] = None
    expect_max_energy: Optional[float] = None
    expect_min_energy: Optional[float] = None
    check_consistency: bool = False


@dataclass
class TestResult:
    name: str
    passed: bool
    reason: str
    query: str
    top_result: str = ""
    iterations: int = 0
    elapsed_ms: float = 0.0
    confidence: float = 0.0
    strategy: str = ""


# ---------------------------------------------------------------------------
# Core test battery (12 cases)
# ---------------------------------------------------------------------------

TEST_CASES: List[TestCase] = [
    TestCase("relevance_happy_pop",         "upbeat happy pop music",                  expect_mood="happy",     expect_genre="pop"),
    TestCase("relevance_chill_lofi",        "chill lofi beats for studying",           expect_mood="chill",     expect_max_energy=0.6),
    TestCase("relevance_high_energy_workout","intense high energy music for the gym",  expect_min_energy=0.7),
    TestCase("relevance_rock",              "heavy rock music",                        expect_genre="rock"),
    TestCase("relevance_jazz_relax",        "relaxing jazz for a sunday afternoon",    expect_mood="relaxed",   expect_max_energy=0.6),
    TestCase("relevance_ambient_sleep",     "calm ambient music to fall asleep to",    expect_max_energy=0.5),
    TestCase("relevance_hip_hop",           "hip hop rap music",                       expect_genre="hip-hop"),
    TestCase("edge_case_empty_query",       ""),
    TestCase("edge_case_unknown_genre",     "bossa nova music"),
    TestCase("edge_case_conflicting_prefs", "very intense peaceful relaxing heavy metal"),
    TestCase("consistency_chill_lofi",      "lofi chill beats",                        check_consistency=True),
    TestCase("consistency_pop_happy",       "happy pop song",                          check_consistency=True),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_test(tc: TestCase, agent: MusicAgent) -> TestResult:
    t0 = time.perf_counter()
    try:
        result = agent.run(tc.query, k=5)
    except Exception as exc:
        logger.exception("Test '%s' crashed: %s", tc.name, exc)
        return TestResult(
            name=tc.name, passed=False,
            reason=f"Exception: {exc}", query=tc.query,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )

    elapsed = (time.perf_counter() - t0) * 1000
    recs = result.recommendations
    if not recs:
        return TestResult(name=tc.name, passed=False, reason="No recommendations",
                          query=tc.query, elapsed_ms=elapsed)

    top_song = recs[0][0]
    top3     = [r[0] for r in recs[:3]]
    avg_e    = sum(float(s.get("energy", 0.5)) for s in top3) / len(top3)

    if tc.expect_mood:
        if not any(s.get("mood", "").lower() == tc.expect_mood.lower() for s in top3):
            return TestResult(
                name=tc.name, passed=False,
                reason=f"Expected mood '{tc.expect_mood}' in top 3; got {[s['mood'] for s in top3]}",
                query=tc.query, top_result=top_song["title"],
                iterations=result.iterations, elapsed_ms=elapsed,
                confidence=result.query.confidence, strategy=result.retrieval_strategy,
            )

    if tc.expect_genre:
        if top_song.get("genre", "").lower() != tc.expect_genre.lower():
            return TestResult(
                name=tc.name, passed=False,
                reason=f"Expected genre '{tc.expect_genre}' in top result; got '{top_song.get('genre')}'",
                query=tc.query, top_result=top_song["title"],
                iterations=result.iterations, elapsed_ms=elapsed,
                confidence=result.query.confidence, strategy=result.retrieval_strategy,
            )

    if tc.expect_max_energy is not None and avg_e > tc.expect_max_energy:
        return TestResult(
            name=tc.name, passed=False,
            reason=f"Expected avg energy ≤ {tc.expect_max_energy:.2f}; got {avg_e:.2f}",
            query=tc.query, top_result=top_song["title"],
            iterations=result.iterations, elapsed_ms=elapsed,
            confidence=result.query.confidence, strategy=result.retrieval_strategy,
        )

    if tc.expect_min_energy is not None and avg_e < tc.expect_min_energy:
        return TestResult(
            name=tc.name, passed=False,
            reason=f"Expected avg energy ≥ {tc.expect_min_energy:.2f}; got {avg_e:.2f}",
            query=tc.query, top_result=top_song["title"],
            iterations=result.iterations, elapsed_ms=elapsed,
            confidence=result.query.confidence, strategy=result.retrieval_strategy,
        )

    if tc.check_consistency:
        for _ in range(2):
            r2 = agent.run(tc.query, k=5)
            if not r2.recommendations:
                return TestResult(name=tc.name, passed=False, reason="Consistency: empty on repeat",
                                  query=tc.query, top_result=top_song["title"], elapsed_ms=elapsed)
            if r2.recommendations[0][0]["title"] != top_song["title"]:
                return TestResult(
                    name=tc.name, passed=False,
                    reason=(f"Consistency: first='{top_song['title']}', "
                            f"repeat='{r2.recommendations[0][0]['title']}'"),
                    query=tc.query, top_result=top_song["title"], elapsed_ms=elapsed,
                    confidence=result.query.confidence, strategy=result.retrieval_strategy,
                )

    return TestResult(
        name=tc.name, passed=True, reason="All checks passed",
        query=tc.query, top_result=top_song["title"],
        iterations=result.iterations, elapsed_ms=elapsed,
        confidence=result.query.confidence, strategy=result.retrieval_strategy,
    )


# ---------------------------------------------------------------------------
# STRETCH: RAG quality comparison (basic vs. context-augmented)
# ---------------------------------------------------------------------------

def run_rag_comparison(agent: MusicAgent) -> dict:
    """
    Runs 4 context-rich queries with and without context documents.
    Reports whether context-augmented retrieval changes the top result.
    """
    queries = [
        ("music for a late night study session", "chill"),
        ("something to pump me up at the gym",   "intense"),
        ("songs for a road trip at sunset",      "moody"),
        ("winding down before bed",              "peaceful"),
    ]
    rows = []
    for query, expected_mood in queries:
        # Basic retrieval
        basic_results = agent.rag.retrieve(query, top_k=5)
        basic_top = basic_results[0][0]

        # Context-augmented retrieval
        ctx_results, matched = agent.rag.retrieve_with_context(query, top_k=5)
        ctx_top = ctx_results[0][0]

        changed  = basic_top["title"] != ctx_top["title"]
        improved = ctx_top.get("mood", "").lower() == expected_mood.lower()

        rows.append({
            "query":            query,
            "expected_mood":    expected_mood,
            "basic_top":        basic_top["title"],
            "context_top":      ctx_top["title"],
            "result_changed":   changed,
            "mood_improved":    improved,
            "contexts_matched": [c["name"] for c in matched[:2]],
        })

    improvements = sum(1 for r in rows if r["mood_improved"])
    return {"rows": rows, "improvements": improvements, "total": len(rows)}


# ---------------------------------------------------------------------------
# STRETCH: Profile specialization test
# ---------------------------------------------------------------------------

def run_profile_comparison(songs) -> dict:
    """
    Demonstrates specialization by running two contrast queries under all 5 profiles.
    A vague query (no genre/mood) lets energy_weight diverge results measurably.
    """
    from recommender import recommend_songs

    # happy mood + low energy target: STUDY (high mood_weight) picks the happy song;
    # WORKOUT (high energy_weight) picks the low-energy song closest to 0.4 target.
    prefs = {"mood": "happy", "genre": None, "energy": 0.4}
    query = "happy music with low energy"
    rows = []
    top_titles = set()

    for key in ["balanced", "study", "workout", "party", "acoustic"]:
        profile = get_profile(key)
        recs = recommend_songs(prefs, songs, k=3, profile=profile)
        top = recs[0][0]["title"]
        top_titles.add(top)
        rows.append({
            "profile":      key,
            "top_result":   top,
            "top_score":    round(recs[0][1], 2),
            "top_3_titles": [r[0]["title"] for r in recs[:3]],
            "top_3_genres": [r[0]["genre"]  for r in recs[:3]],
        })

    return {"rows": rows, "distinct_top_results": len(top_titles), "query": query}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: List[TestResult], rag_cmp: dict = None, profile_cmp: dict = None) -> None:
    total  = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_ms = sum(r.elapsed_ms for r in results) / total
    avg_conf = sum(r.confidence for r in results) / total

    border = "=" * 64
    print(f"\n{border}")
    print("  VIBEMATCHER AI — RELIABILITY EVALUATION REPORT")
    print(border)
    print(f"  Tests run  : {total}")
    print(f"  Passed     : {passed}")
    print(f"  Failed     : {total - passed}")
    print(f"  Pass rate  : {passed / total:.0%}")
    print(f"  Avg latency: {avg_ms:.0f} ms/query")
    print(f"  Avg confidence: {avg_conf:.2f}")
    print(border)

    for r in results:
        icon = "[PASS]" if r.passed else "[FAIL]"
        line = f"  {icon}  {r.name}"
        if not r.passed:
            print(line)
            print(f"         Reason   : {r.reason}")
        else:
            strat = f"  strategy={r.strategy}" if r.strategy else ""
            print(f"{line}  ->  {r.top_result}  (iter={r.iterations}, {r.elapsed_ms:.0f}ms{strat})")

    # RAG comparison
    if rag_cmp:
        print(f"\n{border}")
        print("  STRETCH: RAG Enhancement — Basic vs. Context-Augmented")
        print(border)
        for row in rag_cmp["rows"]:
            changed_tag = "[CHANGED]" if row["result_changed"] else "[same]   "
            mood_tag    = "[mood OK]" if row["mood_improved"] else "[mood -] "
            print(f"  {changed_tag} {mood_tag}  \"{row['query'][:42]}\"")
            print(f"           basic={row['basic_top']:<25}  context={row['context_top']}")
            if row["contexts_matched"]:
                print(f"           contexts matched: {row['contexts_matched']}")
        print(f"\n  Mood improvements from context source: "
              f"{rag_cmp['improvements']}/{rag_cmp['total']}")

    # Profile comparison
    if profile_cmp:
        print(f"\n{border}")
        print("  STRETCH: Specialization — Profile Comparison")
        print(f"  Query: \"{profile_cmp['query']}\"")
        print(border)
        for row in profile_cmp["rows"]:
            top3 = ", ".join(row["top_3_titles"])
            print(f"  [{row['profile']:<9}]  score={row['top_score']:.2f}  top-3: {top3}")
        print(f"\n  Distinct top-1 results across 5 profiles: "
              f"{profile_cmp['distinct_top_results']}/5  "
              f"({'measurably different' if profile_cmp['distinct_top_results'] > 1 else 'same #1 — see scores and top-3 for differences'})")

    print(border + "\n")


def save_report(results, rag_cmp=None, profile_cmp=None) -> str:
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(_ROOT, "logs", f"evaluation_{ts}.json")
    payload = {
        "timestamp":  ts,
        "total":      len(results),
        "passed":     sum(1 for r in results if r.passed),
        "pass_rate":  sum(1 for r in results if r.passed) / len(results),
        "avg_latency_ms": sum(r.elapsed_ms for r in results) / len(results),
        "results":    [asdict(r) for r in results],
        "rag_comparison":     rag_cmp,
        "profile_comparison": profile_cmp,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading model and song catalog…")
    csv_path = os.path.join(_ROOT, "data", "songs.csv")
    ctx_path = os.path.join(_ROOT, "data", "music_contexts.json")
    songs    = load_songs(csv_path)
    ctx_docs = load_context_documents(ctx_path) if os.path.exists(ctx_path) else []
    rag      = RAGEngine(songs, context_docs=ctx_docs)
    agent    = MusicAgent(rag)

    print(f"Running {len(TEST_CASES)} core tests…\n")
    results = [run_test(tc, agent) for tc in TEST_CASES]

    # Stretch: RAG comparison
    print("Running RAG comparison (basic vs. context-augmented)…")
    rag_cmp = run_rag_comparison(agent)

    # Stretch: profile comparison
    print("Running profile specialization comparison…")
    profile_cmp = run_profile_comparison(songs)

    print_report(results, rag_cmp, profile_cmp)
    path = save_report(results, rag_cmp, profile_cmp)
    print(f"Report saved to: {path}\n")

    if any(not r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
