# VibeMatcher AI — End-to-End Music Recommendation System

> A natural-language music recommender powered by Retrieval-Augmented Generation, an agentic self-validating pipeline, and a reliability evaluation system. Built as a final Applied AI project.

---

## Original Project (Modules 1–3)

This project began as **VibeMatcher 1.0**, a content-based music recommendation simulation built during Modules 1–3 of the Applied AI course. Its original goal was to demonstrate how streaming platforms like Spotify use audio features — genre, mood, energy, tempo — to score and rank songs against a user's taste profile. The system used a weighted scoring formula (genre +1.5, mood +2.0, energy similarity up to +4.0) applied to a handcrafted catalog of 18 songs, run entirely through a command-line demo with hard-coded user profiles.

---

## Title & Summary

**VibeMatcher AI** transforms that foundation into a fully end-to-end AI system. Instead of fixed profiles, users type natural-language queries like *"heavy rock for the gym"* or *"calm ambient music to wind down"*. The system understands the intent, retrieves semantically relevant songs using a local AI model, re-ranks them by audio features, and explains every step of its reasoning.

**Why it matters:** Most real-world recommenders are black boxes. This system is deliberately transparent — it shows exactly which candidates the AI retrieved, how they were ranked, and why. That transparency is useful both for understanding how AI recommendations work and for building trust in the output.

---

## Architecture Overview

The system is organized into five layers:

```
User Query → [Parser] → [RAG Retriever] → [Content Scorer] → [Validator] → [Explainer] → Output
                                                                   ↑
                                                          retry with relaxed
                                                          constraints if needed
```

**Input Layer** — Users interact via a Streamlit web UI (`src/app.py`) or the CLI (`src/main.py`).

**Agent Pipeline** (`src/agent.py`) — A five-step orchestrator:
1. **Parser** extracts structured intent (mood, genre, energy) from the query using keyword matching
2. **Retriever** uses `RAGEngine` to semantically embed the query and find the 15 most similar songs from the catalog — this is the RAG step
3. **Scorer** applies content-based weighted scoring to those 15 candidates and returns the top 5
4. **Validator** self-checks whether the output actually satisfies the stated intent; if not, it relaxes constraints and retries (up to 3 iterations)
5. **Explainer** generates a plain-English walkthrough of what the AI did

**Data & Models** — `data/songs.csv` (18 songs × 10 features) and the `all-MiniLM-L6-v2` sentence-transformer model, which runs fully locally after a one-time ~90 MB download.

**Reliability Layer** — `evaluate/evaluate.py` runs 12 automated test cases covering relevance, consistency, and edge cases. `tests/test_recommender.py` covers unit behavior with pytest. All activity is logged to `logs/`.

See [system_diagram.md](system_diagram.md) for the full visual diagram.

---

## Setup Instructions

### Prerequisites
- Python 3.9 or higher
- Internet connection for first run (downloads the ~90 MB sentence-transformer model once; after that everything runs offline)

### Step 1 — Clone or download the project

```bash
git clone <your-repo-url>
cd applied-ai-system-project
```

### Step 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `pytest`, `streamlit`, `sentence-transformers`, `scikit-learn`, `numpy`

> On first run, `sentence-transformers` will automatically download the `all-MiniLM-L6-v2` model from HuggingFace. This requires an internet connection once. The model is then cached and all subsequent runs are fully offline. No API keys required.

### Step 4 — Run the app

**Web UI (recommended):**
```bash
python -m streamlit run src/app.py
```
Opens at `http://localhost:8501`

**CLI — interactive mode:**
```bash
python -m src.main
```

**CLI — one-shot query:**
```bash
python -m src.main "heavy rock for working out"
```

**CLI — original demo profiles (no model download needed):**
```bash
python -m src.main --demo
```

### Step 5 — Run tests

```bash
# Unit tests
pytest

# Reliability evaluation (runs 12 test cases, saves JSON report to logs/)
python -m evaluate.evaluate
```

---

## Sample Interactions

### Example 1 — "chill lofi for studying"

**Input:** `chill lofi for studying`

**Parsed intent:** mood=chill, genre=lofi, energy=0.20, context=study

**RAG semantic search found:** Midnight Coding, Library Rain, Focus Flow (closest semantic matches)

**Final recommendations:**
```
#1  Library Rain — Paper Lanterns
    lofi / chill  |  Score: 6.90/9.0
    Why: genre match (+1.5) | mood match (+2.0) | energy similarity (+3.8)

#2  Midnight Coding — LoRoom
    lofi / chill  |  Score: 6.62/9.0
    Why: genre match (+1.5) | mood match (+2.0) | energy similarity (+3.1)

#3  Spacewalk Thoughts — Orbit Bloom
    ambient / chill  |  Score: 5.68/9.0
    Why: mood match (+2.0) | energy similarity (+3.7)
```
**Validation:** Passed in 1 iteration — all top 3 have `chill` mood, average energy 0.35 (well within low-energy target).

---

### Example 2 — "upbeat happy pop music"

**Input:** `upbeat happy pop music`

**Parsed intent:** mood=happy, genre=pop, energy=0.85

**Final recommendations:**
```
#1  Sunrise City — Neon Echo
    pop / happy  |  Score: 8.42/9.0
    Why: genre match (+1.5) | mood match (+2.0) | energy similarity (+3.9) | positive vibes (+1.0)

#2  Rooftop Lights — Indigo Parade
    indie pop / happy  |  Score: 6.84/9.0
    Why: mood match (+2.0) | energy similarity (+3.8) | positive vibes (+1.0)

#3  Gym Hero — Max Pulse
    pop / intense  |  Score: 5.98/9.0
    Why: genre match (+1.5) | energy similarity (+3.5) | positive vibes (+1.0)
```
**Validation:** Passed in 1 iteration — top result is exact genre + mood match with near-perfect score.

---

### Example 3 — Edge case: "bossa nova music" (genre not in catalog)

**Input:** `bossa nova music`

**Parsed intent:** mood=None, genre=None (bossa nova not in catalog), energy=0.5

**What the agent did:** RAG retrieved songs most semantically similar to "bossa nova" — it found jazz and acoustic songs. Content-based scorer ran without a genre filter. Validation relaxed constraints automatically since no mood was specified.

**Final recommendations:**
```
#1  Coffee Shop Stories — Slow Stereo
    jazz / relaxed  |  Score: 3.50/9.0

#2  Island Breeze — Reggae Vibes
    reggae / laid-back  |  Score: 3.30/9.0

#3  Autumn Leaves — Folk Revival
    folk / introspective  |  Score: 3.20/9.0
```
**Behavior:** No crash. System gracefully falls back to semantic similarity — reasonable genre neighbors rather than an empty result.

---

## Design Decisions

### Why RAG instead of expanding the scoring formula?

The original VibeMatcher scored every song against fixed preferences. This works for structured inputs but breaks completely for natural language — "something to zone out to" has no genre or mood keyword to match. RAG lets the system understand the *meaning* of the request, not just its keywords. By first retrieving semantically relevant songs, the content-based scorer operates on a pre-filtered, already-relevant subset, making results more accurate than either approach alone.

**Trade-off:** RAG adds a ~90 MB model dependency and a cold-start download. For a production system with millions of songs, you would use a vector database (Pinecone, Weaviate) rather than in-memory numpy arrays. For 18 songs, numpy is fast enough and keeps dependencies minimal.

### Why keyword NLU instead of a real language model for parsing?

Using a full LLM for query parsing (e.g., GPT or a local Llama model) would add gigabytes of dependencies and require either a paid API or significant local compute. The keyword-based parser in `agent.py` covers the space of queries well enough for the 18-song catalog, and it's completely transparent — you can read exactly what it does. The RAG step handles the cases where keywords miss, because even if "chill" isn't detected as a keyword, the semantic embedding will still retrieve low-energy songs.

**Trade-off:** The parser doesn't understand negation ("no hip hop") or complex intent ("something like Radiohead but happier"). A real NLP layer would be needed for a production system.

### Why an agentic validation loop?

A single-pass system would sometimes return results that technically scored highest but felt wrong — for example, a "workout" query might return a high-energy jazz song that scores well on energy but contradicts the intent. The validator adds a self-check that catches the worst mismatches and retries with relaxed constraints. This pattern (act → check → retry) is a core principle of agentic AI systems.

**Trade-off:** Up to 3 iterations means the system can be slower in edge cases. In practice it almost always passes on the first iteration.

### Why sentence-transformers over a cloud API?

The rubric requires no paid API keys. `sentence-transformers` with `all-MiniLM-L6-v2` is:
- Free and open source (Apache 2.0 license)
- Small enough to download once and cache (~90 MB vs. gigabytes for larger models)
- Fast at inference (embeddings compute in milliseconds after loading)
- Accurate enough for the task — it's specifically trained for semantic similarity

---

## Testing Summary

### What was tested

| Test Type | Tool | Cases | Result |
|-----------|------|-------|--------|
| Unit tests | `pytest` | 2 | 2/2 pass |
| Relevance tests | `evaluate.py` | 7 | Verifies top results match stated mood/genre |
| Consistency tests | `evaluate.py` | 2 | Same query → same top result (deterministic) |
| Edge case tests | `evaluate.py` | 3 | Empty query, unknown genre, conflicting prefs |

### What worked well

- **RAG retrieval is accurate.** For "chill lofi for studying," the top semantic match was `Midnight Coding (lofi/chill)` with similarity 0.547 — exactly right. The sentence-transformer model generalizes well beyond exact keyword matches.
- **The agentic retry loop was never actually needed** in normal testing — validation passed on the first iteration for all reasonable queries. This is a good sign: the combined RAG + CF approach produces aligned results without needing correction.
- **Edge cases handled gracefully.** Empty queries default to "chill music." Unknown genres fall back to semantic similarity. No test caused a crash.

### What didn't work as expected

- **The parser misses negation.** Typing "not rock" still returns rock songs because the keyword "rock" is detected regardless of context.
- **Small catalog limits diversity.** With 18 songs, queries for rare moods (e.g., "angry" or "introspective") return few true matches and the scorer fills the remaining slots with energy-adjacent results.
- **Git Bash suppresses Streamlit's startup output**, making it look like the server is frozen when it's actually loading. Using `python -m streamlit run` from PowerShell or a system terminal resolves this.

### What I learned from testing

Running the evaluation battery revealed that the `focused` mood in songs.csv doesn't match any mood keyword the parser produces — it maps internally to "chill," which is close but not exact. This kind of vocabulary mismatch between the model's labels and user language is a real challenge in production recommenders and something Spotify addresses with hundreds of human-curated mood categories.

---

## Reflection

Building VibeMatcher AI taught me that the gap between a working algorithm and a useful AI system is mostly about robustness and trust. The original scoring formula from Module 1 was technically correct — it ranked songs by the right features. But it couldn't handle how real people actually express what they want. Nobody says "genre: lofi, mood: chill, energy: 0.4" — they say "something to study to."

RAG bridged that gap in a way that felt almost surprising. Embedding a sentence like "something to wind down after a long day" and finding that it's geometrically closest to ambient and folk songs — without any handcrafted rules — demonstrates something important: meaning is structure, and neural networks can learn that structure from text alone.

The agentic validation loop also changed how I think about AI reliability. Instead of accepting the first output, the agent checks its own work against the original intent. This is a small version of the same principle behind reinforcement learning from human feedback — using a signal (did the output match the request?) to improve results. Even a simple rule-based validator made the system meaningfully more trustworthy.

The biggest open question this project left me with: how do you scale trust? With 18 songs and 12 test cases, I can reason about every recommendation manually. Real systems make billions of recommendations daily with no human in the loop. The logging, evaluation, and transparency features I built here are the beginning of an answer — but they only work if someone actually reads the logs. Designing AI systems that remain interpretable at scale seems like one of the most important unsolved problems in the field.

---

## Project Structure

```
applied-ai-system-project/
├── src/
│   ├── recommender.py      # Content-based scoring (Song, UserProfile, Recommender)
│   ├── rag_engine.py       # RAGEngine — semantic search via sentence-transformers
│   ├── agent.py            # MusicAgent — full 5-step agentic pipeline
│   ├── app.py              # Streamlit web UI
│   ├── main.py             # CLI entry point
│   └── logger_config.py    # Logging to logs/
├── data/
│   └── songs.csv           # 18-song catalog with audio features
├── evaluate/
│   └── evaluate.py         # 12-case reliability test battery
├── tests/
│   └── test_recommender.py # pytest unit tests
├── system_diagram.md       # Architecture diagrams (Mermaid + ASCII)
├── model_card.md           # Model documentation
├── requirements.txt
└── README.md
```

---

## Dependencies

| Package | Purpose | License |
|---------|---------|---------|
| `sentence-transformers` | Local semantic embeddings for RAG | Apache 2.0 |
| `scikit-learn` | Cosine similarity computation | BSD |
| `numpy` | Vector math | BSD |
| `streamlit` | Web UI framework | Apache 2.0 |
| `pandas` | Data handling | BSD |
| `pytest` | Unit testing | MIT |

No paid APIs. No accounts required. Fully reproducible from `pip install -r requirements.txt`.

Demo Video link - https://www.loom.com/share/35312ea3922e48e89b07ada9ff6dbe63
What I have learnt: This project reflects my approach to building AI systems that are not only functional, but also interpretable and reliable. I focused on combining multiple techniques  semantic retrieval through RAG, structured content-based scoring, and an agentic validation loop  to create a system that produces meaningful and trustworthy outputs. Rather than treating AI as a black box, I designed VibeMatcher AI to explain its reasoning at every step, which I believe is critical for real-world applications. This project also demonstrates my ability to think beyond individual models and build complete end-to-end systems, including evaluation and edge-case handling. Overall, it shows that I prioritize clarity, robustness, and user trust when designing AI solutions.