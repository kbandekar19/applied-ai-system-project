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


def run_recommendations(user_prefs: dict, songs: list, profile_name: str) -> None:
    """Run and display recommendations for a specific user profile."""
    print(f"\n{'='*70}")
    print(f"🎵 {profile_name.upper()} PROFILE 🎵")
    print(f"{'='*70}")
    print(f"Preferences: {user_prefs['genre'].upper()} music, {user_prefs['mood']} vibes, energy: {user_prefs['energy']}")

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\nTOP 5 RECOMMENDATIONS:\n")
    
    for idx, rec in enumerate(recommendations, 1):
        song, score, explanation = rec
        print(f"#{idx}. {song['title'].upper()}")
        print(f"   Artist: {song['artist']}")
        print(f"   Score: {score:.2f}/9.0")
        print(f"   Why: {explanation}")
        print()
    print("="*70)


def main() -> None:
    # Get the path to the data file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "songs.csv")
    
    songs = load_songs(csv_path) 
    print(f"Loaded songs: {len(songs)}")

    # Define multiple user profiles for testing
    profiles = [
        {
            "name": "High-Energy Pop",
            "prefs": {"genre": "pop", "mood": "happy", "energy": 0.8}
        },
        {
            "name": "Chill Lofi",
            "prefs": {"genre": "lofi", "mood": "chill", "energy": 0.4}
        },
        {
            "name": "Deep Intense Rock",
            "prefs": {"genre": "rock", "mood": "intense", "energy": 0.9}
        },
        # Adversarial/Edge Case Profiles
        {
            "name": "Conflicting: High Energy + Sad Mood",
            "prefs": {"genre": "pop", "mood": "sad", "energy": 0.9}
        },
        {
            "name": "Extreme: Zero Energy + Happy",
            "prefs": {"genre": "pop", "mood": "happy", "energy": 0.0}
        },
        {
            "name": "Non-existent Genre",
            "prefs": {"genre": "classical", "mood": "relaxed", "energy": 0.5}
        },
        {
            "name": "Mixed: Rock + Chill",
            "prefs": {"genre": "rock", "mood": "chill", "energy": 0.6}
        }
    ]

    # Run recommendations for each profile
    for profile in profiles:
        run_recommendations(profile["prefs"], songs, profile["name"])


if __name__ == "__main__":
    main()
