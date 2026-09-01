"""Description similarity for the duplicate module.

Backed by ``all-MiniLM-L6-v2`` sentence embeddings, which catch a work described
in different words — "Construction of CC road" against "Providing and laying
cement concrete road" — where string matching would not.

The model sits behind this interface so it can be swapped. A character-n-gram
TF-IDF fallback is included and is selected automatically when the transformer
cannot be loaded, so the engine degrades rather than failing. Recall drops on
reworded duplicates; nothing crashes.

Embeddings are cached in-process by text, because a corpus of works contains many
identical descriptions and encoding is the slow part.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

logger = logging.getLogger(__name__)

_model = None
_backend: str | None = None
_cache: dict[str, object] = {}


def backend() -> str:
    """Which implementation is in use — reported on the engine status endpoint."""
    _ensure_backend()
    return _backend or "unavailable"


def _ensure_backend() -> None:
    global _model, _backend
    if _backend is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _backend = "sentence-transformers/all-MiniLM-L6-v2"
    except Exception as exc:  # noqa: BLE001 - any failure means fall back
        logger.warning("sentence-transformers unavailable (%s); using TF-IDF fallback", exc)
        _model = None
        _backend = "char-ngram-tfidf (fallback)"


def preload(texts: Iterable[str]) -> None:
    """Encode a whole corpus in one batch.

    Encoding 4,000 descriptions one pair at a time is the difference between
    seconds and minutes, so the runner calls this before scoring.
    """
    _ensure_backend()
    if _model is None:
        return
    pending = sorted({t for t in texts if t and t not in _cache})
    if not pending:
        return
    vectors = _model.encode(pending, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    for text, vector in zip(pending, vectors, strict=True):
        _cache[text] = vector


def similarity(a: str, b: str) -> float:
    """Cosine similarity in [0, 1]."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    _ensure_backend()
    if _model is None:
        return _ngram_similarity(a, b)

    for text in (a, b):
        if text not in _cache:
            _cache[text] = _model.encode([text], normalize_embeddings=True)[0]
    va, vb = _cache[a], _cache[b]
    return float(max(0.0, min(1.0, float(va @ vb))))


# --------------------------------------------------------------------------
# Fallback
# --------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+")


def _ngrams(text: str, n: int = 4) -> set[str]:
    normalised = " ".join(_WORD.findall(text.lower()))
    if len(normalised) < n:
        return {normalised}
    return {normalised[i : i + n] for i in range(len(normalised) - n + 1)}


def _ngram_similarity(a: str, b: str) -> float:
    """Jaccard overlap of character 4-grams.

    Deliberately not word overlap: it survives the word-order and inflection
    differences that separate two descriptions of the same work.
    """
    ga, gb = _ngrams(a), _ngrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)
