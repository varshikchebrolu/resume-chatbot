import re
from google import genai
from google.genai import types
import numpy as np

api_key = "AIzaSyApRvkcjfhf0wm-r4cuBRG3_VabS0TTs6k"

client = genai.Client(api_key=api_key)


def findCosineSimilarity(queryVector, chunkVectors):
    query_vec = np.array(queryVector)
    chunks_vec = np.array(chunkVectors)

    dot_product = np.dot(chunks_vec, query_vec)
    query_norm = np.linalg.norm(query_vec)
    chunks_norm = np.linalg.norm(chunks_vec, axis=1)

    cosineSimilarity = dot_product / (query_norm * chunks_norm)

    return cosineSimilarity


def loadAndChunk(filepath="data/resume.txt", max_chunk_size=100):
    """Reads a file and splits it into sentence-aware chunks."""
    with open(filepath) as f:
        text = f.read().strip()

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

    chunks = [c for c in chunks if c]
    return chunks


def embedChunks(chunks):
    """Embeds a list of text chunks and returns their vectors."""
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=chunks,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return [emb.values for emb in response.embeddings]


def findClosestChunks(userQuery, chunks, chunkEmbeddings, top_n=3, similarity_threshold=0.65):
    """Finds the top-N chunks most similar to the user query."""
    userQueryEncoding = client.models.embed_content(
        model="gemini-embedding-001",
        contents=userQuery,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    query_vec = userQueryEncoding.embeddings[0].values

    similarities = findCosineSimilarity(query_vec, chunkEmbeddings)

    # Get indices sorted by highest similarity
    sorted_indices = np.argsort(similarities)[::-1]
    top_indices = [i for i in sorted_indices if similarities[i] > similarity_threshold][:top_n]

    results = []
    for i in top_indices:
        results.append((float(similarities[i]), chunks[i]))

    return results


def generatePromptWithSimilarities(userPrompt, closestChunk_results):
    context = "\n\n".join([chunk for score,chunk in closestChunk_results])
    
    prompt = f"""Answer the question based ONLY on this context. DO not hallucinate. Say I don't know if you don't have the relavent context.
    
    {context}
    
    Question: {userPrompt}
    
    """
    
    return prompt
