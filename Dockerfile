# Dockerfile dla ParagonWeb
# Wersja webowa - tylko Cloud (Mistral OCR + OpenAI API)

FROM python:3.13-slim

# Instalujemy minimalne zależności systemowe
# Poppler jest potrzebny do konwersji PDF na obraz (nawet w trybie Cloud OCR)
# Tesseract nie jest potrzebny w trybie Cloud OCR
RUN apt-get update && apt-get install -y \
    curl \
    poppler-utils \
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
# 8081 - NiceGUI frontend
EXPOSE 8000 8081

# Oznaczamy, że jesteśmy w kontenerze Docker
ENV DOCKER_CONTAINER=true
# Wymuszamy tryb Cloud
ENV USE_CLOUD_AI=true
ENV USE_CLOUD_OCR=true

# Start - uruchamiamy zarówno backend jak i frontend
CMD ["sh", "-c", "python server.py & python web_app.py"]

