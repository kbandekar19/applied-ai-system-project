"""
VibeMatcher AI — Streamlit web interface.

Run from the project root:
    streamlit run src/app.py
"""

import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in [_ROOT, _HERE]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

from recommender import load_songs
from rag_engine import RAGEngine, load_context_documents
from agent import MusicAgent
from profiles import PROFILES, get_profile
from logger_config import setup_logger

logger = setup_logger("app")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="VibeMatcher AI",
    page_icon="🎵",
    layout="centered",
)

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #6d28d9 0%, #db2777 100%);
        border-radius: 16px;
        padding: 36px 28px 28px;
        margin-bottom: 28px;
        text-align: center;
    }
    .hero h1 { color: #fff; font-size: 2.4rem; font-weight: 800; margin: 0 0 6px; letter-spacing: -0.5px; }
    .hero p  { color: rgba(255,255,255,0.82); font-size: 1.05rem; margin: 0; }

    .song-card {
        background: #16162a;
        border-radius: 14px;
        padding: 18px 20px 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(124,58,237,0.25);
        box-shadow: 0 4px 16px rgba(0,0,0,0.35);
    }

    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #7c3aed, #db2777);
        color: #fff;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 20px;
        margin-bottom: 8px;
        letter-spacing: 0.04em;
    }
    .song-title  { font-size: 1.12rem; font-weight: 700; color: #f1f5f9; line-height: 1.3; }
    .song-artist { font-size: 0.88rem; color: #94a3b8; margin-top: 3px; }

    .tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.74rem;
        font-weight: 600;
        margin: 8px 4px 0 0;
    }
    .tag-genre { background: rgba(124,58,237,0.18); color: #a78bfa; border: 1px solid rgba(124,58,237,0.35); }
    .tag-mood  { background: rgba(219,39,119,0.18); color: #f472b6; border: 1px solid rgba(219,39,119,0.35); }
    .tag-tempo { background: rgba(15,118,110,0.18); color: #34d399; border: 1px solid rgba(15,118,110,0.3); }

    .energy-wrap  { margin-top: 12px; }
    .energy-label { font-size: 0.72rem; color: #64748b; margin-bottom: 4px; }
    .energy-track {
        background: rgba(255,255,255,0.07);
        border-radius: 4px;
        height: 6px;
        width: 100%;
        overflow: hidden;
    }
    .energy-fill { height: 6px; border-radius: 4px; }

    .match-reason { font-size: 0.78rem; color: #a78bfa; margin-top: 10px; font-style: italic; }

    .vibe-pill {
        display: inline-block;
        background: rgba(52,211,153,0.12);
        border: 1px solid rgba(52,211,153,0.3);
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 0.84rem;
        color: #34d399;
        margin-bottom: 18px;
    }

    .section-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #475569;
        margin: 4px 0 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOOD_EMOJI = {
    "happy": "😊", "chill": "😌", "intense": "💪", "focused": "🎯",
    "moody": "🌙", "peaceful": "🕊️", "euphoric": "🎉", "melancholic": "💭",
    "aggressive": "🔥", "laid-back": "🛋️", "relaxed": "☀️", "romantic": "💕",
}

CONTEXT_LABEL = {
    "studying_focus":        "Studying & Focus",
    "workout_gym":           "Workout & Gym",
    "sleep_relax":           "Winding Down",
    "driving_roadtrip":      "Road Trip",
    "party_social":          "Party",
    "morning_motivation":    "Morning Motivation",
    "evening_chill":         "Evening Chill",
    "emotional_introspective": "Emotional & Reflective",
}

STEP_LABEL = {
    "PLAN":     "Chose a search approach",
    "PARSE":    "Understood your request",
    "RETRIEVE": "Searched the catalog",
    "SCORE":    "Ranked the songs",
    "VALIDATE": "Checked the results",
    "EXPLAIN":  "Generated explanations",
}


def human_reason(raw: str) -> str:
    parts = []
    r = raw.lower()
    if "genre match" in r:
        parts.append("genre fits your vibe")
    if "mood match" in r:
        parts.append("mood is a great match")
    if "energy similarity" in r:
        parts.append("energy level feels right")
    if "positive vibes" in r:
        parts.append("uplifting sound")
    if not parts:
        parts.append("matches your overall vibe")
    return " · ".join(parts).capitalize()


def energy_bar_html(pct: int) -> str:
    if pct < 40:
        color, label = "#34d399", "Low energy"
    elif pct < 70:
        color, label = "#fb923c", "Medium energy"
    else:
        color, label = "#f43f5e", "High energy"
    return (
        f'<div class="energy-wrap">'
        f'<div class="energy-label">{label} &nbsp; {pct}%</div>'
        f'<div class="energy-track">'
        f'<div class="energy-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Cached resource loading
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Getting VibeMatcher ready…")
def load_agent():
    csv_path = os.path.join(_ROOT, "data", "songs.csv")
    ctx_path = os.path.join(_ROOT, "data", "music_contexts.json")
    songs = load_songs(csv_path)
    ctx_docs = load_context_documents(ctx_path) if os.path.exists(ctx_path) else []
    rag = RAGEngine(songs, context_docs=ctx_docs)
    return MusicAgent(rag), len(songs), len(ctx_docs)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="hero"><h1>🎵 VibeMatcher</h1>'
    '<p>Describe your mood and I\'ll find the perfect tracks for you.</p></div>',
    unsafe_allow_html=True,
)

agent, catalog_size, _ctx_count = load_agent()

query = st.text_input(
    "",
    placeholder="e.g. chill lo-fi for studying · upbeat pop for my morning · heavy metal for the gym…",
    label_visibility="collapsed",
    key="query_input",
)

col1, col2 = st.columns([3, 1])
with col1:
    profile_key = st.selectbox(
        "Listening context",
        list(PROFILES.keys()),
        format_func=lambda k: PROFILES[k].name,
        index=0,
        help="Adjusts how songs are ranked for different situations.",
    )
with col2:
    k = st.selectbox("Songs", [3, 5, 7], index=1)

submitted = st.button("Match My Vibe ✨", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if submitted:
    if not query.strip():
        st.warning("Type what you're feeling above — I'll take care of the rest.")
    else:
        with st.spinner("Finding your perfect tracks…"):
            profile = get_profile(profile_key)
            result = agent.run(query.strip(), k=int(k), profile=profile)

        # Vibe context badge
        if result.matched_contexts:
            labels = [
                CONTEXT_LABEL.get(c["name"], c["name"].replace("_", " ").title())
                for c in result.matched_contexts[:2]
            ]
            st.markdown(
                f'<div class="vibe-pill">✨ Tuned to your '
                f'<strong>{" & ".join(labels)}</strong> vibe</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<div class="section-label">Your {len(result.recommendations)} picks</div>',
            unsafe_allow_html=True,
        )

        for rank, (song, _score, cf_reason) in enumerate(result.recommendations, 1):
            energy_pct = int(float(song.get("energy", 0)) * 100)
            mood       = song.get("mood", "")
            mood_icon  = MOOD_EMOJI.get(mood.lower(), "🎵")
            genre      = song.get("genre", "").upper()
            tempo_raw  = song.get("tempo_bpm", "?")
            try:
                tempo_label = f"{int(float(tempo_raw))} BPM"
            except (ValueError, TypeError):
                tempo_label = "? BPM"

            st.markdown(
                f'<div class="song-card">'
                f'<div class="rank-badge">#{rank}</div>'
                f'<div class="song-title">{song["title"]}</div>'
                f'<div class="song-artist">{song["artist"]}</div>'
                f'<div>'
                f'  <span class="tag tag-genre">{genre}</span>'
                f'  <span class="tag tag-mood">{mood_icon} {mood.capitalize()}</span>'
                f'  <span class="tag tag-tempo">♩ {tempo_label}</span>'
                f'</div>'
                f'{energy_bar_html(energy_pct)}'
                f'<div class="match-reason">✦ {human_reason(cf_reason)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Behind the scenes — collapsed by default
        with st.expander("Behind the scenes", expanded=False):
            st.caption("How VibeMatcher understood your request and chose these songs.")
            q = result.query
            c1, c2, c3 = st.columns(3)
            c1.metric("Detected mood",  q.mood  or "open")
            c2.metric("Detected genre", q.genre or "any")
            c3.metric("Energy target",  f"{q.energy:.0%}")

            if result.matched_contexts:
                st.markdown("**Context cues used**")
                for c in result.matched_contexts:
                    label = CONTEXT_LABEL.get(c["name"], c["name"].replace("_", " ").title())
                    st.markdown(f"- {label} (relevance: {c['similarity']:.0%})")

            if result.reasoning_chain:
                st.markdown("**Decision steps**")
                for step in result.reasoning_chain:
                    label = STEP_LABEL.get(step.step, step.step.capitalize())
                    icon = "✅" if ("PASS" in step.decision or step.step == "EXPLAIN") else (
                           "⚠️" if "FAIL" in step.decision else "▸")
                    st.markdown(f"{icon} **{label}** — {step.rationale}")

# ---------------------------------------------------------------------------
# Sidebar — structured filter
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Filter songs")
    st.caption("Browse by genre, mood, or energy — no description needed.")

    s_genre = st.selectbox(
        "Genre",
        ["any", "pop", "rock", "lofi", "hip-hop", "jazz", "ambient",
         "synthwave", "indie pop", "country", "metal", "classical",
         "electronic", "blues", "reggae", "folk"],
    )
    s_mood = st.selectbox(
        "Mood",
        ["any", "happy", "chill", "intense", "focused", "moody",
         "peaceful", "euphoric", "melancholic", "aggressive", "laid-back", "relaxed"],
        format_func=lambda m: (f"{MOOD_EMOJI.get(m, '')} {m.capitalize()}"
                               if m != "any" else "Any mood"),
    )
    s_energy = st.slider(
        "Energy level", 0.0, 1.0, 0.5, 0.05,
        help="0 = very calm  ·  1 = very intense",
    )
    s_profile = st.selectbox(
        "Listening context",
        list(PROFILES.keys()),
        format_func=lambda k: PROFILES[k].name,
        key="sidebar_profile",
    )
    s_k = st.selectbox("Songs", [3, 5, 7], index=1, key="sidebar_k")

    if st.button("Search", use_container_width=True):
        from recommender import recommend_songs as _rs, load_songs as _ls
        _songs = _ls(os.path.join(_ROOT, "data", "songs.csv"))
        _prefs = {
            "mood":   None if s_mood  == "any" else s_mood,
            "genre":  None if s_genre == "any" else s_genre,
            "energy": s_energy,
        }
        _recs = _rs(_prefs, _songs, k=int(s_k), profile=get_profile(s_profile))
        st.divider()
        st.markdown(f"**{PROFILES[s_profile].name} picks**")
        for rank, (song, _score, _reason) in enumerate(_recs, 1):
            mood_icon = MOOD_EMOJI.get(song["mood"].lower(), "🎵")
            st.markdown(f"**#{rank} {song['title']}**")
            st.caption(
                f"{song['artist']} · {song['genre'].upper()} · "
                f"{mood_icon} {song['mood'].capitalize()}"
            )

    st.divider()
    st.caption("VibeMatcher AI · Runs entirely on your machine.")
