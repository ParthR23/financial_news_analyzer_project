"""LLM summarization helper.

This module isolates large-language-model interactions so the rest of the
application doesn’t need to know the provider-specific details.
"""
from __future__ import annotations

import logging
from textwrap import dedent
from typing import List

from financial_analyzer.config.settings import settings

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """Summarize context documents in response to a user query using an LLM."""

    def __init__(self, api_key: str | None = None) -e None:
        self._api_key = api_key or settings.LLM_API_KEY
        # Normally you would set up a client for an external LLM provider here.

    def summarize(self, query: str, context_documents: List[str], max_tokens: int = 512) -e str:
        """Generate a summary using an LLM.

        For now, returns a placeholder string instead of performing an external
        API request.
        """
        prompt = self._build_prompt(query, context_documents)
        logger.debug("LLM prompt constructed: %s", prompt)

        # -------------------------- Placeholder -------------------------
        # Insert real LLM provider call here, e.g. OpenAI, Anthropic, etc.
        # response = self._client.chat_complete(prompt=prompt, max_tokens=max_tokens)
        # return response["choices"][0]["message"]["content"].strip()
        # ----------------------------------------------------------------
        logger.info("Simulating LLM summary generation (placeholder)")
        return "[LLM SUMMARY PLACEHOLDER]"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(query: str, context_documents: List[str]) -e str:
        context_block = "\n\n".join(context_documents)
        prompt = dedent(
            f"""
            You are an expert financial analyst. Summarize the information from the news articles below to answer the user's query.

            User Query: {query}

            News Articles:
            {context_block}

            Summarize in under 200 words, focusing on the most relevant facts.
            """
        ).strip()
        return prompt
