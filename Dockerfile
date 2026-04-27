FROM python:3.11-slim

# Dependente sistem pentru OpenCV, PyMuPDF si Tesseract
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

# Encoding UTF-8 obligatoriu
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN echo "20260427-hematii-mcv" > /app/BUILD_VERSION

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# start.sh: detecteaza tessdata path si porneste uvicorn
RUN printf '#!/bin/sh\n\
TDATA=$(find /usr/share/tesseract-ocr -name "ron.traineddata" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)\n\
if [ -n "$TDATA" ]; then export TESSDATA_PREFIX="$TDATA"; fi\n\
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 4 --timeout-keep-alive 300 --limit-max-requests 1000 --limit-max-requests-jitter 100\n' > /start.sh \
    && chmod +x /start.sh

CMD ["/bin/sh", "/start.sh"]
