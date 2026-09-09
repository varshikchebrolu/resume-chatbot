"""Lightweight RAG helpers: chunk, embed, and retrieve resume snippets."""
import re
from functools import lru_cache

import numpy as np
from google import genai
from google.genai import types

from core.config import get_settings

_settings = get_settings()


@lru_cache
def _get_client() -> genai.Client:
    """Lazily build a single genai client, validating the key at first use."""
    if not _settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
        )
    return genai.Client(api_key=_settings.google_api_key)


def findCosineSimilarity(queryVector, chunkVectors):
    query_vec = np.array(queryVector)
    chunks_vec = np.array(chunkVectors)

    dot_product = np.dot(chunks_vec, query_vec)
    query_norm = np.linalg.norm(query_vec)
    chunks_norm = np.linalg.norm(chunks_vec, axis=1)

    return dot_product / (query_norm * chunks_norm)


def loadAndChunkText(text, max_chunk_size=100):
    """Splits raw text into sentence-aware chunks."""
    text = (text or "").strip()

    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks, current = [], ""

    for sentence in sentences:
        if len(current) + len(sentence) > max_chunk_size and current:
            chunks.append(current.strip())
            current = ""
        current += sentence + " "

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


def embedChunks(chunks):
    """Embeds a list of text chunks and returns their vectors."""
    response = _get_client().models.embed_content(
        model=_settings.embedding_model,
        contents=chunks,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return [emb.values for emb in response.embeddings]


def findClosestChunks(userQuery, chunks, chunkEmbeddings, top_n=3, similarity_threshold=0.65):
    """Finds the top-N chunks most similar to the user query."""
    userQueryEncoding = _get_client().models.embed_content(
        model=_settings.embedding_model,
        contents=userQuery,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    query_vec = userQueryEncoding.embeddings[0].values

    similarities = findCosineSimilarity(query_vec, chunkEmbeddings)
    sorted_indices = np.argsort(similarities)[::-1]
    top_indices = [i for i in sorted_indices if similarities[i] > similarity_threshold][:top_n]

    return [(float(similarities[i]), chunks[i]) for i in top_indices]
