"""Voyage AI 임베딩 래퍼."""
import os
import logging

logger = logging.getLogger(__name__)

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
_client = None


def get_voyage_client():
    """Voyage AI 클라이언트 (lazy init)."""
    global _client
    if _client is None:
        if not VOYAGE_API_KEY:
            logger.warning("VOYAGE_API_KEY 미설정, 임베딩 비활성화")
            return None
        import voyageai
        _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def embed_text(text: str) -> list[float] | None:
    """단일 텍스트 임베딩."""
    client = get_voyage_client()
    if not client:
        return None
    try:
        result = client.embed([text], model="voyage-3-lite")
        return result.embeddings[0]
    except Exception as e:
        logger.error(f"임베딩 오류: {e}")
        return None


def embed_batch(texts: list[str]) -> list[list[float]] | None:
    """배치 임베딩."""
    client = get_voyage_client()
    if not client:
        return None
    try:
        result = client.embed(texts, model="voyage-3-lite")
        return result.embeddings
    except Exception as e:
        logger.error(f"배치 임베딩 오류: {e}")
        return None
