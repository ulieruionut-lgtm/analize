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

# Encoding UTF-8 obligatoriu — fara el, print() cu diacritice cade pe cp1250/ASCII in container
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injectează PORT; dacă lipsește, --port gol face uvicorn să iasă imediat → healthcheck eșuat
ENV PORT=8000
CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
