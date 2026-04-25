FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY nlp/ ./nlp/
COPY data/ ./data/
COPY prompts/ ./prompts/
COPY config.py .
COPY ingestion/ ./ingestion/
COPY translation/ ./translation/
COPY audio/ ./audio/

# Create required runtime directories
RUN mkdir -p logs .cache/llm .cache/analysis audio/output

# Prevent HuggingFace Hub retries (saves ~23s on cold start)
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 300 --workers 1"]
