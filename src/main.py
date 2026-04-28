"""
VibeMatcher AI — command-line interface.

Usage:
    # Interactive natural-language mode
    python -m src.main

    # One-shot query
    python -m src.main "chill lofi for studying"

    # Run demo with preset profiles (original behaviour)
    python -m src.main --demo
"""

import os
import sys

def main() -> None:
    # Resolve paths before any local imports so they work from any CWD
    _src = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(_src)
    for _p in [_root, _src]:
        if _p not in sys.path:
            sys.path.insert(0, _p)

    from recommender import load_songs, recommend_songs

    csv_path = os.path.join(_root, "data", "songs.csv")
    songs = load_songs(csv_path)
    print(f"Loaded {len(songs)} songs from catalog.\n")

    # ------------------------------------------------------------------
    # --demo flag: run the original 7 fixed profiles (no model needed)
    # ------------------------------------------------------------------
    if "--demo" in sys.argv:
        profiles = [
            {"name": "High-Energy Pop",               "prefs": {"genre": "pop",       "mood": "happy",   "energy": 0.8}},
            {"name": "Chill Lofi",                    "prefs": {"genre": "lofi",      "mood": "chill",   "energy": 0.4}},
            {"name": "Deep Intense Rock",             "prefs": {"genre": "rock",      "mood": "intense", "energy": 0.9}},
            {"name": "Conflicting: High Energy + Sad","prefs": {"genre": "pop",       "mood": "sad",     "energy": 0.9}},
            {"name": "Extreme: Zero Energy + Happy",  "prefs": {"genre": "pop",       "mood": "happy",   "energy": 0.0}},
            {"name": "Non-existent Genre",            "prefs": {"genre": "classical", "mood": "relaxed", "energy": 0.5}},
            {"name": "Mixed: Rock + Chill",           "prefs": {"genre": "rock",      "mood": "chill",   "energy": 0.6}},
        ]
        for p in profiles:
            _print_profile(p["prefs"], p["name"], recommend_songs)
        return

    # For AI-powered modes, import RAG + Agent (downloads model on first run)
    from rag_engine import RAGEngine
    from agent import MusicAgent

    # ------------------------------------------------------------------
    # Single query from argv
    # ------------------------------------------------------------------
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        query = " ".join(args)
        _run_agent_query(query, songs)
        return

    # ------------------------------------------------------------------
    # Interactive loop
    # ------------------------------------------------------------------
    print("VibeMatcher AI  (type 'quit' to exit, '--demo' for preset profiles)\n")
    print("Building semantic index (downloading model on first run)…")
    rag = RAGEngine(songs)
    agent = MusicAgent(rag)

    while True:
        try:
            query = input("What music are you in the mood for? > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break
        if query == "--demo":
            main_demo(recommend_songs, songs)
            continue

        _run_agent_query(query, songs, rag=rag, agent=agent)


def _run_agent_query(query: str, songs, rag=None, agent=None) -> None:
    import sys, os
    _src = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(_src)
    for _p in [_root, _src]:
        if _p not in sys.path:
            sys.path.insert(0, _p)
    from rag_engine import RAGEngine
    from agent import MusicAgent

    if rag is None:
        print("Building semantic index…")
        rag = RAGEngine(songs)
    if agent is None:
        agent = MusicAgent(rag)

    print(f"\nSearching for: \"{query}\"\n")
    result = agent.run(query, k=5)

    print("=" * 70)
    print(f"RESULTS  (validation={'passed' if result.validation_passed else 'relaxed'}, "
          f"{result.iterations} iteration(s))")
    print("=" * 70)

    for rank, (song, score, reason) in enumerate(result.recommendations, 1):
        print(f"\n#{rank}  {song['title'].upper()}")
        print(f"    Artist : {song['artist']}")
        print(f"    Genre  : {song['genre']}  |  Mood: {song['mood']}")
        print(f"    Score  : {score:.2f}/9.0")
        print(f"    Why    : {reason}")

    print("\n--- How AI found these ---")
    print(result.explanation)
    print("=" * 70 + "\n")


def _print_profile(prefs: dict, name: str, recommend_songs_fn) -> None:
    from recommender import load_songs
    import os, sys
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "songs.csv")
    songs = load_songs(csv_path)

    print(f"\n{'='*70}")
    print(f"  {name.upper()}")
    print(f"{'='*70}")
    print(f"  Preferences: genre={prefs.get('genre')}, mood={prefs.get('mood')}, energy={prefs.get('energy')}")
    print("\n  TOP 5 RECOMMENDATIONS:\n")
    for idx, (song, score, explanation) in enumerate(recommend_songs_fn(prefs, songs, k=5), 1):
        print(f"  #{idx}. {song['title']} — {song['artist']}")
        print(f"       Score: {score:.2f}/9.0  |  {explanation}\n")
    print("=" * 70)


def main_demo(recommend_songs_fn, songs):
    profiles = [
        {"name": "High-Energy Pop",    "prefs": {"genre": "pop",  "mood": "happy",   "energy": 0.8}},
        {"name": "Chill Lofi",         "prefs": {"genre": "lofi", "mood": "chill",   "energy": 0.4}},
        {"name": "Deep Intense Rock",  "prefs": {"genre": "rock", "mood": "intense", "energy": 0.9}},
    ]
    for p in profiles:
        _print_profile(p["prefs"], p["name"], recommend_songs_fn)


if __name__ == "__main__":
    main()
