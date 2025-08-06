"""Sentiment analysis utility leveraging Hugging Face Transformers.

Wraps a transformers pipeline to make sentiment predictions easy to use in the
rest of the application.
"""
from __future__ import annotations

from typing import Tuple

from transformers import pipeline  # type: ignore


class SentimentAnalyzer:
    """Thin wrapper over a Hugging Face sentiment-analysis pipeline."""

    _MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

    def __init__(self) -> None:
        # Lazy-load pipeline; caching handled internally by 🤗 Transformers.
        self._pipeline = pipeline("sentiment-analysis", model=self._MODEL_NAME)

    def analyze(self, text: str) -> Tuple[str, float]:
        """Return sentiment label (e.g., POSITIVE/NEGATIVE) and confidence score."""
        result = self._pipeline(text, truncation=True)[0]
        return result["label"], float(result["score"])
