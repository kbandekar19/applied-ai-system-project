from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song and its attributes. Required by tests/test_recommender.py"""
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
    """Represents a user's taste preferences. Required by tests/test_recommender.py"""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """OOP recommendation interface. Required by tests/test_recommender.py"""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects ranked by content-based score."""
        scored = []
        for song in self.songs:
            score = 0.0
            if song.genre.lower() == user.favorite_genre.lower():
                score += 1.5
            if song.mood.lower() == user.favorite_mood.lower():
                score += 2.0
            score += 4.0 * (1 - abs(song.energy - user.target_energy))
            if song.valence > 0.7 and user.favorite_mood.lower() == "happy":
                score += 1.0
            scored.append((song, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a brief explanation of why this song matches the user."""
        reasons = []
        if song.genre.lower() == user.favorite_genre.lower():
            reasons.append("genre match")
        if song.mood.lower() == user.favorite_mood.lower():
            reasons.append("mood match")
        if abs(song.energy - user.target_energy) < 0.2:
            reasons.append("energy match")
        if user.likes_acoustic and song.acousticness > 0.5:
            reasons.append("acoustic preference")
        return ", ".join(reasons) if reasons else "general recommendation"

    def recommend_from_candidates(
        self,
        user_prefs: Dict,
        candidate_songs: List[Dict],
        k: int = 5,
    ) -> List[Tuple[Dict, float, str]]:
        """Re-rank a list of song dicts (from load_songs / RAG) by content-based score."""
        return recommend_songs(user_prefs, candidate_songs, k=k)


# ---------------------------------------------------------------------------
# Functional API (used by main.py, agent.py, evaluate.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from CSV and return as a list of dicts with numeric fields converted."""
    import csv

    float_cols = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}
    int_cols = {"id"}

    songs: List[Dict] = []
    with open(csv_path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for col in float_cols:
                if col in row:
                    row[col] = float(row[col])
            for col in int_cols:
                if col in row:
                    row[col] = int(row[col])
            songs.append(row)
    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    genre_weight: float = 1.5,
    mood_weight: float = 2.0,
    energy_weight: float = 4.0,
    valence_bonus: float = 1.0,
) -> Tuple[float, List[str]]:
    """Score a song dict against user preferences; return (score, list_of_reasons).

    Weight parameters are exposed so ScoringProfiles can adjust emphasis
    (stretch feature: fine-tuning / specialization).
    """
    score = 0.0
    reasons: List[str] = []

    # Genre match
    if user_prefs.get("genre") and song.get("genre", "").lower() == user_prefs["genre"].lower():
        score += genre_weight
        reasons.append(f"genre match (+{genre_weight:.1f})")

    # Mood match
    if user_prefs.get("mood") and song.get("mood", "").lower() == user_prefs["mood"].lower():
        score += mood_weight
        reasons.append(f"mood match (+{mood_weight:.1f})")

    # Energy similarity
    if "energy" in song and "energy" in user_prefs:
        e_score = energy_weight * (1 - abs(float(song["energy"]) - float(user_prefs["energy"])))
        score += e_score
        reasons.append(f"energy similarity (+{e_score:.1f})")

    # Valence bonus for happy mood
    if float(song.get("valence", 0)) > 0.7 and (user_prefs.get("mood") or "") == "happy":
        score += valence_bonus
        reasons.append(f"positive vibes (+{valence_bonus:.1f})")

    return score, reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    profile=None,
) -> List[Tuple[Dict, float, str]]:
    """Score every song in `songs` and return the top k as (song, score, explanation) tuples.

    Accepts an optional ScoringProfile to apply specialised weights.
    """
    weights = profile.to_dict() if profile is not None else {}
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, **weights)
        explanation = " | ".join(reasons) if reasons else "No matching preferences"
        scored.append((song, score, explanation))
    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
