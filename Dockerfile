FROM python:3.11-slim

# Instaleaza Tesseract OCR cu pachetele de limba română și engleză direct din apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Encoding UTF-8 obligatoriu
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# start.sh: detecteaza tessdata path si porneste uvicorn
RUN printf '#!/bin/sh\n\
TDATA=$(find /usr/share/tesseract-ocr -name "ron.traineddata" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)\n\
if [ -n "$TDATA" ]; then export TESSDATA_PREFIX="$TDATA"; fi\n\
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"\n' > /start.sh \
    && chmod +x /start.sh

CMD ["/bin/sh", "/start.sh"]
