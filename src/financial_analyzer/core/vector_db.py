"""Wrapper around ChromaDB for storing and querying news article embeddings.

This module centralizes vector database interactions so other parts of the
application can remain agnostic of the underlying storage implementation.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import chromadb  # type: ignore
from sentence_transformers import SentenceTransformer  # type: ignore

from financial_analyzer.config.settings import settings


class VectorDB:
    """Interface for adding and retrieving documents from ChromaDB."""

    _DEFAULT_COLLECTION_NAME = "financial_news"
    _EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, collection_name: str | None = None) -> None:
        collection_name = collection_name or self._DEFAULT_COLLECTION_NAME

        # Ensure storage path exists
        db_path = Path(settings.VECTOR_DB_PATH).expanduser().resolve()
        db_path.mkdir(parents=True, exist_ok=True)

        # Persistent ChromaDB client
        self._client = chromadb.PersistentClient(path=str(db_path))

        # Create or get collection
        self._collection = self._client.get_or_create_collection(name=collection_name)

        # Initialize embedder once per process
        self._embedder = SentenceTransformer(self._EMBEDDING_MODEL_NAME)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_documents(self, texts: Sequence[str], metadatas: Sequence[Dict[str, Any]]) -> None:
        """Add texts and their metadata to the vector store."""
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must be the same length")

        ids = [str(uuid.uuid4()) for _ in texts]
        embeddings = self._embedder.encode(list(texts)).tolist()
        self._collection.add(
            ids=ids,
            documents=list(texts),
            embeddings=embeddings,
            metadatas=list(metadatas),
        )

    def query_documents(self, query_text: str, n: int = 5) -> List[Tuple[str, Dict[str, Any]]]:
        """Return the *n* most similar documents to *query_text*."""
        query_embedding = self._embedder.encode([query_text]).tolist()
        results = self._collection.query(query_embeddings=query_embedding, n_results=n)
        documents: List[str] = results.get("documents", [[]])[0]
        metadatas: List[Dict[str, Any]] = results.get("metadatas", [[]])[0]
        return list(zip(documents, metadatas))
