"""
Scoring profiles — pre-defined weight configurations that specialize
the recommender's behaviour for different listening contexts.

This is the "fine-tuning / specialization" stretch feature.  Each profile
adjusts the same scoring formula with different emphasis, producing
measurably different recommendations for the same query.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoringProfile:
    name: str
    description: str
    genre_weight: float   # points for genre match          (default 1.5)
    mood_weight: float    # points for mood match           (default 2.0)
    energy_weight: float  # max points for energy proximity (default 4.0)
    valence_bonus: float  # bonus for positive songs        (default 1.0)

    def to_dict(self) -> Dict:
        return {
            "genre_weight":   self.genre_weight,
            "mood_weight":    self.mood_weight,
            "energy_weight":  self.energy_weight,
            "valence_bonus":  self.valence_bonus,
        }


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

PROFILES: Dict[str, ScoringProfile] = {
    "balanced": ScoringProfile(
        name="Balanced",
        description="Default weights — equal emphasis on genre, mood, and energy.",
        genre_weight=1.5,
        mood_weight=2.0,
        energy_weight=4.0,
        valence_bonus=1.0,
    ),
    "study": ScoringProfile(
        name="Study Session",
        description="Emphasises mood and penalises energy extremes. Best for focus music.",
        genre_weight=1.0,
        mood_weight=3.0,
        energy_weight=2.5,
        valence_bonus=0.5,
    ),
    "workout": ScoringProfile(
        name="Workout",
        description="Heavily weights energy proximity. Best for high-intensity sessions.",
        genre_weight=1.5,
        mood_weight=1.0,
        energy_weight=6.0,
        valence_bonus=0.5,
    ),
    "party": ScoringProfile(
        name="Party / Dance",
        description="Boosts genre match and positive valence. Best for upbeat social listening.",
        genre_weight=2.5,
        mood_weight=1.5,
        energy_weight=3.0,
        valence_bonus=2.0,
    ),
    "acoustic": ScoringProfile(
        name="Acoustic / Chill",
        description="Boosts genre and valence. Best for mellow, organic-sounding music.",
        genre_weight=2.5,
        mood_weight=2.0,
        energy_weight=2.0,
        valence_bonus=2.0,
    ),
}

DEFAULT_PROFILE = PROFILES["balanced"]


def get_profile(name: str) -> ScoringProfile:
    """Return a profile by key, falling back to balanced if unknown."""
    return PROFILES.get(name.lower(), DEFAULT_PROFILE)
