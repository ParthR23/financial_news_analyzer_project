"""financial_analyzer.core package

Re-export key classes so they can be imported directly from
``financial_analyzer.core``::

    from financial_analyzer.core import LLMSummarizer, SentimentAnalyzer, VectorDB
"""

from .llm import LLMSummarizer  # noqa: F401
from .sentiment import SentimentAnalyzer  # noqa: F401
from .vector_db import VectorDB  # noqa: F401
