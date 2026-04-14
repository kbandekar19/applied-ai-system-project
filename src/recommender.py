from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and convert numeric columns to appropriate types."""
    import csv
    
    print(f"Loading songs from {csv_path}...")
    songs = []
    
    # Columns that should be converted to numeric types
    float_columns = {'energy', 'tempo_bpm', 'valence', 'danceability', 'acousticness'}
    int_columns = {'id'}
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convert numeric columns to float or int for math operations
            for col in float_columns:
                if col in row:
                    row[col] = float(row[col])
            for col in int_columns:
                if col in row:
                    row[col] = int(row[col])
            songs.append(row)
    
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a song against user preferences and return score with reasoning.
    
    Experimental weight shift: Genre match reduced to +1.5, Energy similarity increased to up to +4.0.
    """
    score = 0.0
    reasons = []
    
    # Genre match: +1.5 points (experimental: half the original importance)
    if song.get('genre', '').lower() == user_prefs.get('genre', '').lower():
        score += 1.5
        reasons.append("genre match (+1.5)")
    
    # Mood match: +2.0 points
    if song.get('mood', '').lower() == user_prefs.get('mood', '').lower():
        score += 2.0
        reasons.append("mood match (+2.0)")
    
    # Energy similarity: Calculate how close song energy is to user target
    # Score ranges from 0 to 4.0 based on proximity (experimental: double the original maximum)
    if 'energy' in song and 'energy' in user_prefs:
        energy_score = 4.0 * (1 - abs(float(song['energy']) - float(user_prefs['energy'])))
        score += energy_score
        reasons.append(f"energy similarity (+{energy_score:.1f})")
    
    # Valence bonus: +1.0 if song is positive and user likes happy moods
    if float(song.get('valence', 0)) > 0.7 and user_prefs.get('mood', '').lower() == 'happy':
        score += 1.0
        reasons.append("positive vibes (+1.0)")
    
    return (score, reasons)

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score all songs and return top k recommendations with explanations."""
    # Score all songs using a list comprehension (Pythonic approach)
    # This creates tuples of (song, score, explanation) for every song
    scored_songs = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " + ".join(reasons) if reasons else "No matching preferences"
        scored_songs.append((song, score, explanation))
    
    # Use sorted() instead of .sort() to:
    # - Return a new list without modifying the original
    # - Allow chaining operations after sorting
    # - Keep the original songs list unchanged (immutability)
    # sorted() is generally preferred in functional programming style
    ranked_songs = sorted(scored_songs, key=lambda x: x[1], reverse=True)
    
    # Return top k results
    return ranked_songs[:k]
