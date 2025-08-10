#!/bin/bash
# This script runs the entire financial news analyzer project end-to-end.

echo "--- Starting Data Ingestion: Running Scraper ---"
python3 -m src.financial_analyzer.ingestion.scraper

echo "\n--- Starting Data Processing: Running Embedder ---"
python3 -m src.financial_analyzer.processing.embedder

echo "\n--- Starting API Server ---"
uvicorn src.financial_analyzer.api.main:app --reload