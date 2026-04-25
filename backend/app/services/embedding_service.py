import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model %s...", settings.EMBEDDING_MODEL)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded")
    return _model


def generate_embedding(text: str) -> list[float]:
    model = get_model()
    # normalize_embeddings=True gives unit vectors → dot product = cosine similarity
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    return float(np.dot(a_arr, b_arr))


def build_embed_text(error_type: str, message: str, stack_trace: Optional[str] = None) -> str:
    text = f"{error_type}: {message}"
    if stack_trace:
        # First 500 chars of stack trace carry most signal
        text += f"\n{stack_trace[:500]}"
    return text
