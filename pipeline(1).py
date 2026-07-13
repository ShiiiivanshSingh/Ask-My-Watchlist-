import json
import os
import re
import time
import uuid
import hashlib
import numpy as np


class HashingEmbedder:
    def __init__(self, dim=1024, ngram_range=(3, 5)):
        self.dim = dim
        self.ngram_range = ngram_range

    STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "what", "how",
                 "when", "where", "who", "which", "of", "to", "in", "on",
                 "for", "and", "or", "our", "it", "its", "be", "do", "does",
                 "i", "my", "did", "have", "has", "having", "think", "seen",
                 "watch", "watched", "rate", "rated", "rating", "review",
                 "like", "liked", "about", "did"}

    def _ngrams(self, text):
        words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in self.STOPWORDS]
        grams = list(words)
        grams.extend(" ".join(words[i:i + 2]) for i in range(len(words) - 1))
        return grams

    def _vector(self, text):
        vec = np.zeros(self.dim, dtype=np.float32)
        for gram in self._ngrams(text):
            h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        return np.stack([self._vector(t) for t in texts]).astype(np.float32)

    def get_sentence_embedding_dimension(self):
        return self.dim


class SentenceTransformerEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)

    def get_sentence_embedding_dimension(self):
        return self.model.get_sentence_embedding_dimension()


class VectorIndex:
    def __init__(self, dim):
        self.dim = dim
        self.vectors = np.zeros((0, dim), dtype=np.float32)
        self.records = []

    def add(self, vector, record):
        self.vectors = np.vstack([self.vectors, vector.reshape(1, -1)])
        self.records.append(record)

    def search(self, query_vector, top_k=1):
        if len(self.records) == 0:
            return []
        sims = self.vectors @ query_vector.reshape(-1, 1)
        sims = sims.flatten()
        idx = np.argsort(-sims)[:top_k]
        return [(self.records[i], float(sims[i])) for i in idx]

    def save(self, path):
        np.save(path + ".npy", self.vectors)
        with open(path + ".json", "w") as f:
            json.dump(self.records, f)

    def load(self, path):
        if os.path.exists(path + ".npy") and os.path.exists(path + ".json"):
            self.vectors = np.load(path + ".npy")
            with open(path + ".json") as f:
                self.records = json.load(f)


class SemanticCache:
    def __init__(self, embedder, threshold=0.92, path="cache_store"):
        self.embedder = embedder
        self.threshold = threshold
        self.path = path
        self.index = VectorIndex(embedder.get_sentence_embedding_dimension())
        self.index.load(path)

    def lookup(self, query):
        vec = self.embedder.encode(query)[0]
        hits = self.index.search(vec, top_k=1)
        if hits and hits[0][1] >= self.threshold:
            return hits[0][0]["answer"], hits[0][1]
        return None, hits[0][1] if hits else 0.0

    def store(self, query, answer, source):
        vec = self.embedder.encode(query)[0]
        record = {
            "id": str(uuid.uuid4()),
            "query": query,
            "answer": answer,
            "source": source,
            "ts": time.time(),
        }
        self.index.add(vec, record)
        self.index.save(self.path)


class LocalKB:
    def __init__(self, embedder, confidence_threshold=0.6, path="kb_store"):
        self.embedder = embedder
        self.confidence_threshold = confidence_threshold
        self.path = path
        self.index = VectorIndex(embedder.get_sentence_embedding_dimension())
        self.index.load(path)

    def add_documents(self, chunks):
        vecs = self.embedder.encode(chunks)
        for text, vec in zip(chunks, vecs):
            self.index.add(vec, {"text": text})
        self.index.save(self.path)

    def query(self, question, top_k=3):
        vec = self.embedder.encode(question)[0]
        hits = self.index.search(vec, top_k=top_k)
        if not hits or hits[0][1] < self.confidence_threshold:
            return None, hits[0][1] if hits else 0.0
        context = "\n".join(h[0]["text"] for h in hits)
        return context, hits[0][1]


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks


class Pipeline:
    def __init__(self, api_client, embedder=None, cache_threshold=0.2, kb_threshold=0.08, store_dir="store"):
        os.makedirs(store_dir, exist_ok=True)
        self.embedder = embedder or HashingEmbedder()
        self.cache = SemanticCache(self.embedder, cache_threshold, os.path.join(store_dir, "cache"))
        self.kb = LocalKB(self.embedder, kb_threshold, os.path.join(store_dir, "kb"))
        self.api_client = api_client

    def add_knowledge(self, text):
        self.kb.add_documents(chunk_text(text))

    def ask(self, query):
        cached_answer, score = self.cache.lookup(query)
        if cached_answer is not None:
            return {"answer": cached_answer, "source": "cache", "score": score}

        context, kb_score = self.kb.query(query)
        if context is not None:
            answer = self.api_client.answer_with_context(query, context)
            self.cache.store(query, answer, "kb")
            return {"answer": answer, "source": "kb", "score": kb_score}

        answer = self.api_client.answer(query)
        self.cache.store(query, answer, "api")
        return {"answer": answer, "source": "api", "score": 0.0}
