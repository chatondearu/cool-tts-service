#!/bin/sh
# Fail fast if model weights are missing or Hub download fails; then start uvicorn.
set -eu
cd /app
python ensure_model.py
exec "$@"
