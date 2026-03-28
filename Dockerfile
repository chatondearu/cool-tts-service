# TTS Server - Docker Image
# 
# Build:
#   docker-compose build

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ .

# Create directories for voices and cache (voice .wav files come from COPY app/ and/or volume mount)
RUN mkdir -p /app/voices/default /app/voices/custom /app/cache

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose FastAPI port
EXPOSE 8000

# Allow long first-time Hub download before /health is expected (empty volume)
HEALTHCHECK --interval=30s --timeout=10s --start-period=720s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]