# Dockerfile dla ParagonWeb
# Używa lekkiego obrazu Python

FROM python:3.13-slim

# Instalujemy zależności systemowe
# Tesseract i Poppler są opcjonalne (jeśli używamy Cloud OCR, nie są potrzebne)
# Ale instalujemy je na wszelki wypadek dla trybu lokalnego
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    tesseract-ocr-pol \
    poppler-utils \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopiujemy zależności i instalujemy
COPY ReceiptParser/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy kod
COPY . .

# Utwórz katalogi na dane
RUN mkdir -p /app/ReceiptParser/data /app/uploads /app/logs

# Wystawiamy porty
# 8000 - FastAPI backend
# 8080 - NiceGUI frontend
EXPOSE 8000 8080

# Oznaczamy, że jesteśmy w kontenerze Docker (dla automatycznej konfiguracji Ollama)
ENV DOCKER_CONTAINER=true

# Start - uruchamiamy zarówno backend jak i frontend
# W produkcji można użyć supervisord lub osobnych kontenerów
CMD ["sh", "-c", "python server.py & python web_app.py"]

