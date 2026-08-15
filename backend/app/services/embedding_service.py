import hashlib
import logging
import threading
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model = None
_model_lock = threading.Lock()


def generate_fingerprint(error_type: str, message: str, stack_trace: Optional[str] = None) -> str:
    first_trace_line = stack_trace.strip().split("\n")[0] if stack_trace else ""
    key = f"{error_type}|{message[:100]}|{first_trace_line}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def build_embed_text(error_type: str, message: str, stack_trace: Optional[str] = None) -> str:
    text = f"{error_type}: {message}"
    if stack_trace:
        text += f"\n{stack_trace[:500]}"
    return text


def get_model():
    """Load the sentence-transformer once, on first use. Returns None if semantic
    clustering is disabled or the model cannot be loaded — callers fall back to
    fingerprint-only clustering."""
    global _model

    if not settings.ENABLE_SEMANTIC_CLUSTERING:
        return None

    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    logger.info("Loading embedding model %s ...", settings.EMBEDDING_MODEL)
                    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
                    logger.info("Embedding model loaded")
                except Exception as exc:
                    logger.warning(
                        "Embedding model unavailable, falling back to fingerprint-only "
                        "clustering: %s", exc,
                    )
                    return None

    return _model


def generate_embedding(
    error_type: str, message: str, stack_trace: Optional[str] = None
) -> Optional[list[float]]:
    """384-dim vector for an error, or None if embeddings are unavailable."""
    model = get_model()
    if model is None:
        return None

    try:
        text = build_embed_text(error_type, message, stack_trace)
        return model.encode(text, normalize_embeddings=True).tolist()
    except Exception as exc:
        logger.warning("Embedding generation failed: %s", exc)
        return None
