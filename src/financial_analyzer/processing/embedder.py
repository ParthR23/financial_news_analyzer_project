"""financial_analyzer.processing.embedder

PySpark job to transform raw article JSON files stored in S3 into dense vector
embeddings and persist them into ChromaDB via the project's ``VectorDB``
wrapper.

Execution environment requirements:
    - PySpark (Spark 3.x)
    - sentence-transformers
    - boto3 (implicit via Spark's S3 client when using Hadoop AWS module)
    - chromadb (or whichever backend is used by the VectorDB abstraction)

The job can be submitted either with ``spark-submit`` or executed locally with
``python -m financial_analyzer.processing.embedder`` provided the necessary
Spark & AWS environment variables are configured.
"""
from __future__ import annotations

import json
import os
from typing import List

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf
from pyspark.sql.types import ArrayType, FloatType

from sentence_transformers import SentenceTransformer

try:
    # Attempt to use the project's VectorDB abstraction.
    from financial_analyzer.core.vector_db import VectorDB  # type: ignore
except ImportError:  # pragma: no cover
    # Fallback stub so that the script can still be imported for docs/tests if
    # the full core module hierarchy is not present.
    class VectorDB:  # type: ignore
        def __init__(self, collection_name: str):
            from chromadb import Client  # type: ignore

            self._client = Client()
            self._collection = self._client.get_or_create_collection(collection_name)

        def add_document(self, doc_id: str, metadata: dict, embedding: List[float]):  # noqa: D401,E501
            self._collection.add(documents=[metadata.get("content", "")], ids=[doc_id], metadatas=[metadata], embeddings=[embedding])


try:
    from settings import S3_BUCKET_NAME  # type: ignore
except ImportError:  # pragma: no cover
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

S3_PREFIX = os.getenv("RAW_ARTICLE_PREFIX", "raw_articles")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "financial_news")


# ---------------------------------------------------------------------------
# Spark UDF for embeddings
# ---------------------------------------------------------------------------

def _make_embed_udf(model_name: str):
    """Return a Spark UDF that embeds text using *model_name*."""

    # The model variable will be lazily initialised inside executors. Spark will
    # serialise this closure and ship it to worker nodes.
    def _embed(text: str | None):  # type: ignore
        # Lazy load to avoid re-initialising on every row.
        if not hasattr(_embed, "_model"):
            _embed._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
        if text is None:
            return None
        # SentenceTransformer returns numpy array; convert to list of floats
        vec = _embed._model.encode(text)  # type: ignore[attr-defined]
        return vec.tolist()

    return udf(_embed, ArrayType(FloatType()))


# ---------------------------------------------------------------------------
# Main job logic
# ---------------------------------------------------------------------------

def run_job():
    """Execute the embedding pipeline."""
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME must be configured via settings or env var.")

    spark = (
        SparkSession.builder.appName("financial_news_embedder")
        # Typical Hadoop AWS settings can be passed via spark-submit --conf, so we keep builder minimal.
        .getOrCreate()
    )

    s3_uri = f"s3a://{S3_BUCKET_NAME}/{S3_PREFIX}/*.json"
    df = spark.read.json(s3_uri)

    embed_udf = _make_embed_udf(MODEL_NAME)
    df_with_embeddings = df.withColumn("embedding", embed_udf(col("content")))

    # Collect small-ish dataset to driver; for very large sets this should be
    # batched/streamed instead.
    results = (
        df_with_embeddings.select("url", "title", "published", "content", "embedding")
        .where(col("embedding").isNotNull())
        .collect()
    )

    vectordb = VectorDB(collection_name=COLLECTION_NAME)

    for row in results:
        vectordb.add_document(
            doc_id=row["url"],
            metadata={
                "title": row["title"],
                "published": row["published"],
                "content": row["content"],
            },
            embedding=row["embedding"],
        )

    spark.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    run_job()

