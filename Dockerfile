# --- Stage 1: Build Stage ---
# Use a specific Python version for reproducibility
FROM python:3.10-slim-buster AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
# Copy only requirements to leverage Docker layer caching
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# --- Stage 2: Final Stage ---
FROM python:3.10-slim-buster

# Create a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Install dependencies from the wheels built in the previous stage
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the application source code
COPY ./src .

# Change ownership of the directory to the non-root user
RUN chown -R appuser:appuser /home/appuser

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "financial_analyzer.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
```markdown
# FILE: README.md

# Real-Time Financial News Analysis & Summarization Service

This project is an end-to-end AI service that ingests financial news articles in real-time, performs sentiment analysis, and provides AI-generated summaries on demand through a REST API.

## 🚀 Features

-   **Real-Time Data Ingestion**: Scrapes news articles from multiple financial RSS feeds.
-   **AI-Powered Summarization**: Uses a Retrieval-Augmented Generation (RAG) system to provide concise summaries of news related to a specific query.
-   **Sentiment Analysis**: Provides sentiment scores for any given text.
-   **Scalable Architecture**: Built with a modular, microservice-oriented design and containerized with Docker for easy deployment.
-   **Cloud-Native**: Designed to leverage cloud services like AWS S3 for storage and can be deployed on any modern cloud platform.

## 🏛️ Architecture

The project follows a standard data engineering and MLOps workflow:

1.  **Ingestion**: A Python script (`scraper.py`) periodically scrapes RSS feeds and stores raw articles as JSON files in an AWS S3 bucket.
2.  **Processing & Embedding**: A PySpark job (`embedder.py`) reads the raw data from S3, processes it, generates vector embeddings for the article content using Sentence-Transformers, and loads the data into a ChromaDB vector store.
3.  **API Service**: A FastAPI application serves the AI models through a REST API. It exposes endpoints for summarization and sentiment analysis.
4.  **RAG Logic**: When a user queries the `/summarize` endpoint, the API retrieves the most relevant articles from the vector database and feeds them as context to a Large Language Model (LLM) to generate a high-quality summary.
5.  **Deployment**: The entire application is containerized using Docker, making it portable and easy to deploy on services like Google Cloud Run or AWS ECS.

## 🛠️ Tech Stack

-   **Backend**: FastAPI, Python 3.10
-   **Data Processing**: Apache Spark (PySpark)
-   **AI / ML**: Hugging Face Transformers, Sentence-Transformers, LangChain
-   **Database**: ChromaDB (Vector Store)
-   **Cloud**: AWS S3
-   **Deployment**: Docker

## ⚙️ Setup and Installation

### Prerequisites

-   Python 3.10+
-   Docker
-   AWS Account and credentials configured

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ParthR23/financial_news_analyzer_project.git](https://github.com/ParthR23/financial_news_analyzer_project.git)
    cd financial_news_analyzer_project
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your credentials:
    ```
    AWS_ACCESS_KEY_ID=your_aws_access_key
    AWS_SECRET_ACCESS_KEY=your_aws_secret_key
    S3_BUCKET_NAME=your_s3_bucket_name
    LLM_API_KEY=your_llm_api_key
    ```

4.  **Run the application:**
    ```bash
    uvicorn financial_analyzer.api.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## 🐳 Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t financial-analyzer .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:8000 --env-file .env financial-analyzer
    ```

##  API Endpoints

-   `POST /summarize`: Get a summary of news related to a query.
    -   **Body**: `{"query": "What is the latest news on Tesla?"}`
-   `POST /sentiment`: Get the sentiment of a piece of text.
    -   **Body**: `{"query": "The stock market saw significant gains today."}`

Access the interactive API documentation at `http://127.0.0.1:8000/docs`.