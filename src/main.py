"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import os
from recommender import load_songs, recommend_songs


def main() -> None:
    # Get the path to the data file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "songs.csv")
    
    songs = load_songs(csv_path) 
    print(f"Loaded songs: {len(songs)}")

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    print(f"\nUser Profile: {user_prefs['genre'].upper()} music, {user_prefs['mood']} vibes, energy: {user_prefs['energy']}")

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "="*70)
    print("🎵 TOP 5 RECOMMENDATIONS 🎵")
    print("="*70 + "\n")
    
    for idx, rec in enumerate(recommendations, 1):
        # You decide the structure of each returned item.
        # A common pattern is: (song, score, explanation)
        song, score, explanation = rec
        print(f"#{idx}. {song['title'].upper()}")
        print(f"   Artist: {song['artist']}")
        print(f"   Score: {score:.2f}/9.0")
        print(f"   Why: {explanation}")
        print()
    print("="*70)


if __name__ == "__main__":
    main()
