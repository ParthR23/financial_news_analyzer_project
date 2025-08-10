from fastapi import APIRouter
from src.financial_analyzer.api.schemas import QueryRequest, SentimentResponse, SummaryResponse
from src.financial_analyzer.core import VectorDB, SentimentAnalyzer, LLMSummarizer
from src.financial_analyzer.config import settings

router = APIRouter()

# --- Instantiate our core components ---
# This is a simple way to manage instances for a small app.
# For larger apps, you might use a dependency injection framework.
vector_db = VectorDB()
sentiment_analyzer = SentimentAnalyzer()
# FIX: Pass the required api_key from the settings
llm_summarizer = LLMSummarizer(api_key=settings.LLM_API_KEY)


@router.post("/summarize", response_model=SummaryResponse)
def get_summary(request: QueryRequest):
    """
    Takes a user query, finds relevant news articles, and returns an AI-generated summary.
    """
    # 1. Query the vector database to find relevant documents
    relevant_docs = vector_db.query_documents(query_text=request.query, n_results=3)

    # 2. Use the LLM to generate a summary based on the context
    summary = llm_summarizer.summarize(query=request.query, context_documents=relevant_docs)
    
    return SummaryResponse(summary=summary)


@router.post("/sentiment", response_model=SentimentResponse)
def get_sentiment(request: QueryRequest):
    """
    Takes a text query and returns its sentiment score.
    """
    result = sentiment_analyzer.analyze(text=request.query)
    return SentimentResponse(label=result['label'], score=result['score'])