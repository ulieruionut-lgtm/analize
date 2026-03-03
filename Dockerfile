FROM python:3.11-slim

# Instaleaza Tesseract OCR + pachetul pentru limba romana si engleza
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ron \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
