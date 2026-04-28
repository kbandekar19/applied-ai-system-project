"""
RAG Engine — semantic index over the song catalog using sentence-transformers.

STRETCH FEATURE — RAG Enhancement:
  Supports a second data source (music_contexts.json) alongside the song catalog.
  retrieve_with_context() queries both indexes and boosts song scores when a
  context document bridges the vocabulary gap between query and song descriptions.

On first run the model (~90 MB) is downloaded automatically from HuggingFace and
cached locally; subsequent runs are fully offline.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from logger_config import setup_logger

logger = setup_logger("rag_engine")

MODEL_NAME = "all-MiniLM-L6-v2"
CONTEXT_BOOST = 0.15    # similarity bonus per matching context document
CONTEXT_THRESHOLD = 0.30  # minimum context similarity to apply a boost


def _song_to_text(song: Dict) -> str:
    """Convert a song dict into a rich natural-language description for embedding."""
    energy = float(song.get("energy", 0.5))
    tempo = float(song.get("tempo_bpm", 100))
    valence = float(song.get("valence", 0.5))
    danceability = float(song.get("danceability", 0.5))
    acousticness = float(song.get("acousticness", 0.5))

    energy_label = "high" if energy > 0.7 else "medium" if energy > 0.4 else "low"
    tempo_label = "fast" if tempo > 120 else "moderate" if tempo > 90 else "slow"
    vibe = "positive and uplifting" if valence > 0.7 else "neutral" if valence > 0.45 else "dark or melancholic"

    return (
        f"{song['title']} by {song['artist']}. "
        f"This is a {song['genre']} song with a {song['mood']} mood. "
        f"It has {energy_label} energy ({energy:.2f}) and a {tempo_label} tempo of {tempo:.0f} BPM. "
        f"The overall vibe is {vibe} (valence {valence:.2f}). "
        f"Danceability: {danceability:.2f}, acousticness: {acousticness:.2f}."
    )


def load_context_documents(json_path: str) -> List[Dict]:
    """Load music context documents from the second data source."""
    with open(json_path, "r", encoding="utf-8") as fh:
        docs = json.load(fh)
    logger.info("Loaded %d context documents from %s", len(docs), json_path)
    return docs


class RAGEngine:
    """
    Semantic retrieval engine.

    Basic usage:  retrieve(query)  — song-catalog search only
    Enhanced:     retrieve_with_context(query)  — searches both the song catalog
                  AND a second data source (music_contexts.json) to bridge
                  vocabulary gaps between user queries and song descriptions.
    """

    def __init__(self, songs: List[Dict], context_docs: Optional[List[Dict]] = None):
        logger.info("Initializing RAG engine — loading model '%s'", MODEL_NAME)
        self.model = SentenceTransformer(MODEL_NAME)
        self.songs = songs

        # Source 1: song catalog
        self.descriptions = [_song_to_text(s) for s in songs]
        logger.info("Building song embeddings for %d songs…", len(songs))
        self.embeddings = self.model.encode(self.descriptions, show_progress_bar=False)

        # Source 2: context documents (optional)
        self.context_docs = context_docs or []
        if self.context_docs:
            ctx_texts = [d["text"] for d in self.context_docs]
            logger.info("Building context embeddings for %d documents…", len(ctx_texts))
            self.context_embeddings = self.model.encode(ctx_texts, show_progress_bar=False)
        else:
            self.context_embeddings = None

        logger.info("RAG engine ready (context source: %s)",
                    "enabled" if self.context_docs else "disabled")

    # ------------------------------------------------------------------
    # Basic retrieval — Source 1 only
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """Return top_k songs by semantic similarity to query (song catalog only)."""
        if not query or not query.strip():
            logger.warning("Empty query — returning default ordering")
            return [(s, 0.0) for s in self.songs[:top_k]]

        logger.debug("RAG retrieve (basic): query='%s', top_k=%d", query, top_k)
        query_emb = self.model.encode([query.strip()])
        scores = cosine_similarity(query_emb, self.embeddings)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(self.songs[i], float(scores[i])) for i in top_indices]
        logger.debug("Top result: '%s' (sim=%.3f)", results[0][0]["title"], results[0][1])
        return results

    # ------------------------------------------------------------------
    # Context-augmented retrieval — Sources 1 + 2
    # ------------------------------------------------------------------

    def retrieve_with_context(
        self, query: str, top_k: int = 10
    ) -> Tuple[List[Tuple[Dict, float]], List[Dict]]:
        """
        Retrieve songs using BOTH the song catalog (source 1) and music context
        documents (source 2).

        Returns:
            (ranked_songs, matched_contexts)
            matched_contexts: context documents that exceeded the relevance threshold
        """
        if not query or not query.strip():
            return [(s, 0.0) for s in self.songs[:top_k]], []

        if self.context_embeddings is None:
            logger.debug("No context source loaded; falling back to basic retrieve")
            return self.retrieve(query, top_k), []

        query_emb = self.model.encode([query.strip()])

        # Step 1 — base song similarities
        song_scores = cosine_similarity(query_emb, self.embeddings)[0].copy()

        # Step 2 — context document similarities
        ctx_scores = cosine_similarity(query_emb, self.context_embeddings)[0]
        matched_contexts = []

        for ctx_idx, ctx_sim in enumerate(ctx_scores):
            if ctx_sim < CONTEXT_THRESHOLD:
                continue
            ctx_doc = self.context_docs[ctx_idx]
            matched_contexts.append({**ctx_doc, "similarity": float(ctx_sim)})
            logger.debug(
                "Context match: '%s' (sim=%.3f) — boosting tagged songs",
                ctx_doc["name"], ctx_sim,
            )

            # Step 3 — boost songs whose mood/genre are tagged in this context doc
            for song_idx, song in enumerate(self.songs):
                mood_hit  = song.get("mood",  "").lower() in [t.lower() for t in ctx_doc.get("mood_tags",  [])]
                genre_hit = song.get("genre", "").lower() in [t.lower() for t in ctx_doc.get("genre_tags", [])]
                if mood_hit or genre_hit:
                    boost = CONTEXT_BOOST * ctx_sim  # proportional to context relevance
                    song_scores[song_idx] = min(1.0, song_scores[song_idx] + boost)

        # Step 4 — re-rank with boosted scores
        top_indices = np.argsort(song_scores)[::-1][:top_k]
        results = [(self.songs[i], float(song_scores[i])) for i in top_indices]

        matched_contexts.sort(key=lambda x: x["similarity"], reverse=True)
        logger.info(
            "Context-augmented retrieve: top='%s', contexts_matched=%d",
            results[0][0]["title"], len(matched_contexts),
        )
        return results, matched_contexts

    def get_description(self, song: Dict) -> str:
        """Return the text description used to embed a song."""
        return _song_to_text(song)
