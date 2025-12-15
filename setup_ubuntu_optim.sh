#!/bin/bash
set -e

# Kolory do logowania
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}[INFO] Rozpoczynam konfigurację ParagonOCR dla Ubuntu 24.04 (Optymalizacja GPU GeForce RTX 3060)${NC}"

BASE_DIR=$(dirname "$(realpath "$0")")
VENV_DIR="$BASE_DIR/venv"

# 1. Sprawdzenie i instalacja zależności systemowych
echo -e "${YELLOW}[KROK 1] Sprawdzanie zależności systemowych...${NC}"

if ! command -v tesseract &> /dev/null; then
    echo "Instalacja tesseract-ocr..."
    sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-pol
else
    echo -e "${GREEN}[OK] Tesseract jest zainstalowany. (wersja: $(tesseract --version | head -n 1))${NC}"
fi

if ! command -v pdfimages &> /dev/null; then
    echo "Instalacja poppler-utils..."
    sudo apt-get install -y poppler-utils
else
    echo -e "${GREEN}[OK] Poppler jest zainstalowany.${NC}"
fi

# Biblioteki systemowe dla OpenCV/EasyOCR oraz Tkinter (GUI)
echo "Instalacja bibliotek systemowych dla OpenCV i Tkinter..."
sudo apt-get install -y libgl1 libglib2.0-0 python3-tk

# 2. Sprawdzenie sterowników GPU
echo -e "${YELLOW}[KROK 2] Weryfikacja GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}[OK] Wykryto sterowniki NVIDIA:${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
    echo -e "${RED}[UWAGA] Nie wykryto polecenia nvidia-smi. Upewnij się, że sterowniki są zainstalowane.${NC}"
fi

# 3. Konfiguracja Python venv
echo -e "${YELLOW}[KROK 3] Konfiguracja środowiska Python...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    echo "Tworzenie venv..."
    python3 -m venv "$VENV_DIR"
fi

echo "Aktywacja venv i aktualizacja pip..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

echo "Instalacja zależności z requirements.txt..."
pip install -r "$BASE_DIR/ReceiptParser/requirements.txt"

# 4. Modele Ollama
echo -e "${YELLOW}[KROK 4] Weryfikacja modeli Ollama...${NC}"
if command -v ollama &> /dev/null; then
    # Sprawdź czy serwer działa
    if curl --output /dev/null --silent --fail http://localhost:11434; then
        echo -e "${GREEN}[OK] Serwer Ollama działa.${NC}"
        
        echo "Pobieranie modelu tekstowego: SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M..."
        ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
        
        echo "Pobieranie modelu wizyjnego: llava:latest..."
        ollama pull llava:latest
    else
        echo -e "${RED}[BŁĄD] Serwer Ollama nie odpowiada na porcie 11434.${NC}"
        echo "Uruchom go poleceniem: ollama serve"
    fi
else
    echo -e "${RED}[BŁĄD] Nie znaleziono polecenia 'ollama'. Zainstaluj Ollama ze strony ollama.com${NC}"
fi

# 5. Generowanie pliku .env
echo -e "${YELLOW}[KROK 5] Generowanie zoptymalizowanej konfiguracji .env...${NC}"

cat > "$BASE_DIR/.env" << EOL
# Wygenerowano przez setup_ubuntu_optim.sh dla RTX 3060 / Ryzen 5 5500

# Konfiguracja Ollama
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=llava:latest
TEXT_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=600

# Konfiguracja OCR - Optymalizacja GPU
OCR_ENGINE=easyocr
USE_GPU_OCR=true

# Batch Processing - Optymalizacja CPU (12 wątków)
BATCH_SIZE=8
BATCH_MAX_WORKERS=8

# System
ENABLE_FILE_LOGGING=true
RETRY_MAX_ATTEMPTS=5

# Opcjonalne API
MISTRAL_API_KEY=
EOL

echo -e "${GREEN}[OK] Plik .env utworzony.${NC}"

# Uprawnienia dla skryptu uruchomieniowego
chmod +x "$BASE_DIR/uruchom.sh"

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN} Instalacja zakończona pomyślnie! ${NC}"
echo -e "${GREEN} Aby uruchomić program:${NC}"
echo -e "  ./uruchom.sh"
echo -e "${GREEN}======================================================${NC}"
