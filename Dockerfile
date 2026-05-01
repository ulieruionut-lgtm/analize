FROM python:3.11-slim

# Dependențe sistem pentru OpenCV, PyMuPDF și Tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN echo "20260501-parser-verify-build" > /app/BUILD_VERSION

# Health: CMD expandă $PORT setat de Railway la runtime
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# start.sh: tessdata + uvicorn fără limit-max-requests (OCR/upload lung nu trebuie întrerupt de restart worker)
# WEB_CONCURRENCY: implicit 2; pe instanțe mici (512MB) setează 1 în Railway Variables
RUN printf '%s\n' '#!/bin/sh' 'set -e' \
    'TDATA=$(find /usr/share/tesseract-ocr -name "ron.traineddata" 2>/dev/null | head -1 | xargs dirname 2>/dev/null || true)' \
    'if [ -n "$TDATA" ]; then export TESSDATA_PREFIX="$TDATA"; fi' \
    'WORKERS=${WEB_CONCURRENCY:-2}' \
    'if ! test "$WORKERS" -ge 1 2>/dev/null; then WORKERS=2; fi' \
    'if ! test "$WORKERS" -le 8 2>/dev/null; then WORKERS=8; fi' \
    'exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "$WORKERS" --timeout-keep-alive 300' \
    > /start.sh && chmod +x /start.sh

CMD ["/bin/sh", "/start.sh"]
