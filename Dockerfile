# syntax=docker/dockerfile:1

############################
# Builder stage            #
############################
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system build deps for compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
ENV VENV_PATH="/opt/venv"
RUN python -m venv "$VENV_PATH"
ENV PATH="$VENV_PATH/bin:$PATH"

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

############################
# Runtime stage            #
############################
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder $VENV_PATH $VENV_PATH

# Copy project source
COPY src/ ./src/
COPY requirements.txt ./

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser /app
USER appuser

EXPOSE 80

CMD ["uvicorn", "financial_analyzer.api.main:app", "--host", "0.0.0.0", "--port", "80"]
