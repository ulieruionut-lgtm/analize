FROM python:3.11-slim

# Instaleaza Tesseract OCR si wget pentru descarcarea datelor lingvistice
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tessdata \
    && wget -q -O /tessdata/ron.traineddata \
       https://github.com/tesseract-ocr/tessdata/raw/main/ron.traineddata \
    && wget -q -O /tessdata/eng.traineddata \
       https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# Spune Tesseract unde sa gaseasca datele lingvistice
ENV TESSDATA_PREFIX=/tessdata

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
