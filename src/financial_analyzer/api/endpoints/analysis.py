"""Analysis endpoints providing summarization and sentiment services."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from financial_analyzer.api.schemas import QueryRequest, SentimentResponse, SummaryResponse
from financial_analyzer.core.llm import LLMSummarizer
from financial_analyzer.core.sentiment import SentimentAnalyzer
from financial_analyzer.core.vector_db import VectorDB

# Instantiate core services once per process
vector_db = VectorDB()
sentiment_analyzer = SentimentAnalyzer()
llm_summarizer = LLMSummarizer()

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/summarize", response_model=SummaryResponse, status_code=status.HTTP_200_OK)
async def summarize(request: QueryRequest) -> SummaryResponse:
    """Summarize context documents relevant to the user's query."""
    docs_with_meta = vector_db.query_documents(request.query, n=5)
    if not docs_with_meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No relevant documents found.")

    docs: List[str] = [doc for doc, _ in docs_with_meta]
    summary_text = llm_summarizer.summarize(request.query, docs)
    return SummaryResponse(summary=summary_text)


@router.post("/sentiment", response_model=SentimentResponse, status_code=status.HTTP_200_OK)
async def sentiment(request: QueryRequest) -> SentimentResponse:
    """Analyze sentiment of the given text."""
    label, score = sentiment_analyzer.analyze(request.query)
    return SentimentResponse(label=label, score=score)
