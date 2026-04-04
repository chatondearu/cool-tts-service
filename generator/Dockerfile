# API image: runtime deps only; mount models/ and voices/ at run time (see docker-compose.yml).
# Build from repository root: docker build -f generator/Dockerfile .
FROM python:3.11-slim-bookworm

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.source="https://github.com/chatondearu/cool-tts-service" \
      org.opencontainers.image.title="cool-tts-service-api" \
      org.opencontainers.image.version="${APP_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY generator/requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

COPY VERSION /app/VERSION
COPY generator/main.py generator/tts_engine.py generator/model_bootstrap.py generator/synthesis_logging.py generator/audio_encode.py ./

RUN mkdir -p models voices

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS http://127.0.0.1:9000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
