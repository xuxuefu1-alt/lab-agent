from __future__ import annotations

import logging
import hashlib
import math
import re
import uuid
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, settings


logger = logging.getLogger(__name__)
KB_DIR = BASE_DIR / "data" / "kb"
QDRANT_COLLECTION_PREFIX = "lab_agent_e5_embedding"
QDRANT_MODEL = "intfloat/multilingual-e5-small"
QDRANT_VECTOR_SIZE = 384
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

_documents: list[dict[str, str]] | None = None
_qdrant_client: Any = None


def _chunks(text: str) -> list[str]:
    """将知识文档拆成有重叠的片段，避免检索时丢失段落上下文。"""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + CHUNK_SIZE)
        if end < len(normalized):
            boundary = normalized.rfind("。", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def _load_documents() -> list[dict[str, str]]:
    """读取仓库内版本化知识文档，并缓存分块结果。"""
    global _documents
    if _documents is None:
        loaded: list[dict[str, str]] = []
        for path in sorted(KB_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            for index, chunk in enumerate(_chunks(content)):
                loaded.append({
                    "id": uuid.uuid5(uuid.NAMESPACE_URL, f"{path.name}:{index}:{chunk}").hex,
                    "source": path.name,
                    "content": chunk,
                })
        _documents = loaded
    return _documents


def _tokenize(text: str) -> list[str]:
    """生成中英文检索词，确保无外部向量服务时仍能检索本地知识。"""
    tokens: list[str] = []
    for item in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
        if re.fullmatch(r"[a-z0-9]+", item):
            tokens.append(item)
            continue
        if len(item) == 1:
            tokens.append(item)
            continue
        tokens.extend(item[index:index + 2] for index in range(len(item) - 1))
    return tokens


def _keyword_search(query: str, documents: list[dict[str, str]]) -> list[dict[str, Any]]:
    """使用轻量 BM25 评分作为免费云端服务不可用时的本地兜底。"""
    query_terms = _tokenize(query)
    tokenized = [_tokenize(item["content"]) for item in documents]
    if not query_terms or not tokenized:
        return []

    document_frequency: dict[str, int] = {}
    for tokens in tokenized:
        for term in set(tokens):
            document_frequency[term] = document_frequency.get(term, 0) + 1

    average_length = sum(map(len, tokenized)) / max(1, len(tokenized))
    scores: list[dict[str, Any]] = []
    for document, tokens in zip(documents, tokenized):
        frequencies: dict[str, int] = {}
        for term in tokens:
            frequencies[term] = frequencies.get(term, 0) + 1
        score = 0.0
        for term in set(query_terms):
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            df = document_frequency.get(term, 0)
            inverse_frequency = math.log(1 + (len(tokenized) - df + 0.5) / (df + 0.5))
            denominator = frequency + 1.2 * (0.25 + 0.75 * len(tokens) / max(1, average_length))
            score += inverse_frequency * frequency * 2.2 / denominator
        if score > 0:
            scores.append({**document, "score": score})
    return sorted(scores, key=lambda item: item["score"], reverse=True)[:2]


def _get_qdrant_client():
    """按需连接 Qdrant Cloud，未配置时保持免费本地检索可用。"""
    global _qdrant_client
    if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
        return None
    if _qdrant_client is None:
        from qdrant_client import QdrantClient

        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            cloud_inference=True,
            timeout=12,
        )
    return _qdrant_client


def _search_qdrant(query: str, documents: list[dict[str, str]]) -> list[dict[str, Any]]:
    """从 Qdrant Cloud 查询向量，并在首次访问时写入仓库知识文档。"""
    from qdrant_client import models

    client = _get_qdrant_client()
    if client is None:
        return []
    corpus_text = "\n".join(
        f"{item['source']}:{item['content']}" for item in documents
    )
    corpus_version = hashlib.sha256(corpus_text.encode("utf-8")).hexdigest()[:12]
    collection_name = f"{QDRANT_COLLECTION_PREFIX}_{corpus_version}"
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=QDRANT_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )
    if client.count(collection_name=collection_name, exact=True).count == 0 and documents:
        points = [
            models.PointStruct(
                id=item["id"],
                vector=models.Document(text=item["content"], model=QDRANT_MODEL),
                payload={"source": item["source"], "content": item["content"]},
            )
            for item in documents
        ]
        client.upload_points(
            collection_name=collection_name,
            points=points,
            batch_size=32,
            wait=True,
        )
    response = client.query_points(
        collection_name=collection_name,
        query=models.Document(text=query, model=QDRANT_MODEL),
        limit=5,
        with_payload=True,
    )
    return [
        {
            "source": point.payload.get("source", "knowledge base"),
            "content": point.payload.get("content", ""),
            "score": point.score,
        }
        for point in response.points
        if point.payload and point.score >= 0.35
    ][:2]


def search(query: str) -> str:
    """检索托管向量知识库，并在 Qdrant 不可用时回退至本地 BM25。"""
    documents = _load_documents()
    if not documents:
        return ""

    results: list[dict[str, Any]] = []
    try:
        if settings.QDRANT_URL and settings.QDRANT_API_KEY:
            results = _search_qdrant(query, documents)
    except Exception:
        logger.warning("Qdrant retrieval failed; using local BM25 fallback", exc_info=True)

    if not results:
        results = _keyword_search(query, documents)
    return "\n\n".join(
        f"[{item['source']}\n{item['content']}]" for item in results
    )
