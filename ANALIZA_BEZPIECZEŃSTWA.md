# 🔒 ANALIZA BEZPIECZEŃSTWA - ParagonOCR

**Data analizy:** 2025-01-XX  
**Wersja kodu:** Aktualna (main branch)  
**Analizator:** Security Audit

---

## 📋 SPIS TREŚCI

1. [Podsumowanie wykonawcze](#podsumowanie-wykonawcze)
2. [Krytyczne problemy bezpieczeństwa](#krytyczne-problemy-bezpieczeństwa)
3. [Wysokie ryzyko](#wysokie-ryzyko)
4. [Średnie ryzyko](#średnie-ryzyko)
5. [Niskie ryzyko](#niskie-ryzyko)
6. [Rekomendacje](#rekomendacje)

---

## 📊 PODSUMOWANIE WYKONAWCZE

### Statystyki
- **Krytyczne problemy:** 2
- **Wysokie ryzyko:** 5
- **Średnie ryzyko:** 8
- **Niskie ryzyko:** 6
- **Ogólna ocena bezpieczeństwa:** ⚠️ **ŚREDNIA** (wymaga poprawy)

### Główne obszary problemów
1. **Brak walidacji ścieżek plików** - możliwość path traversal
2. **Niezabezpieczone pliki tymczasowe** - race conditions
3. **Brak walidacji danych wejściowych** - możliwość DoS
4. **Niezabezpieczone przechowywanie danych** - SQLite bez szyfrowania
5. **Logowanie wrażliwych danych** - potencjalny wyciek informacji

---

## 🚨 KRYTYCZNE PROBLEMY BEZPIECZEŃSTWA

### 1. Path Traversal w Obsłudze Plików

**Lokalizacja:** `main.py:69-79`, `ocr.py:54-73`, `mistral_ocr.py:17-60`

**Problem:**
```python
# main.py:69
processing_file_path = file_path  # Brak walidacji ścieżki
if file_path.lower().endswith(".pdf"):
    temp_image_path = convert_pdf_to_image(file_path)  # Używa bezpośrednio
```

**Ryzyko:**
- Atakujący może przekazać ścieżkę typu `../../../etc/passwd` lub `C:\Windows\System32\config\sam`
- Możliwość odczytu/zapisu plików poza katalogiem projektu
- W przypadku GUI: użytkownik może wybrać dowolny plik, ale brak walidacji przed przetwarzaniem

**Dowód koncepcyjny:**
```python
# Jeśli użytkownik wybierze plik:
file_path = "../../../etc/passwd.pdf"
# System spróbuje go przetworzyć jako PDF
```

**Rozwiązanie:**
```python
import os
from pathlib import Path

def validate_file_path(file_path: str, allowed_extensions: list = None) -> Path:
    """Waliduje ścieżkę pliku i normalizuje ją."""
    path = Path(file_path).resolve()
    
    # Sprawdź czy plik istnieje
    if not path.exists():
        raise FileNotFoundError(f"Plik nie istnieje: {file_path}")
    
    # Sprawdź czy to plik (nie katalog)
    if not path.is_file():
        raise ValueError(f"Ścieżka nie wskazuje na plik: {file_path}")
    
    # Sprawdź rozszerzenie (jeśli podano)
    if allowed_extensions:
        if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
            raise ValueError(f"Nieobsługiwane rozszerzenie pliku: {path.suffix}")
    
    # Sprawdź czy plik nie jest za duży (ochrona przed DoS)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"Plik jest za duży (max {MAX_FILE_SIZE / 1024 / 1024} MB)")
    
    return path
```

**Priorytet:** 🔴 **KRYTYCZNY** - Naprawić natychmiast

---

### 2. Niezabezpieczone Pliki Tymczasowe (Race Condition)

**Lokalizacja:** `ocr.py:22-43`, `main.py:130-132`

**Problem:**
```python
# ocr.py:22-24
with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
    images[0].save(tmp_file.name, "JPEG")
    return tmp_file.name  # Zwraca ścieżkę, ale plik może być dostępny dla innych procesów
```

**Ryzyko:**
- Pliki tymczasowe są tworzone z przewidywalnymi nazwami
- Brak ustawienia uprawnień (chmod 600)
- Race condition: inny proces może odczytać plik przed usunięciem
- W systemach wieloużytkownikowych: możliwość odczytu przez innych użytkowników

**Dowód koncepcyjny:**
```bash
# Proces A tworzy: /tmp/tmpXXXXXX.jpg
# Proces B może odczytać plik przed usunięciem
# Jeśli plik zawiera wrażliwe dane (np. dane z paragonu), to wyciek
```

**Rozwiązanie:**
```python
import tempfile
import os
import stat

def create_secure_temp_file(suffix: str = ".jpg") -> str:
    """Tworzy bezpieczny plik tymczasowy z odpowiednimi uprawnieniami."""
    # Użyj mkstemp zamiast NamedTemporaryFile dla większej kontroli
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        # Ustaw uprawnienia: tylko właściciel może czytać/zapisywać
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        # Zwróć deskryptor i ścieżkę
        return fd, path
    except Exception:
        os.close(fd)
        os.unlink(path)
        raise

# W kodzie:
fd, temp_path = create_secure_temp_file(".jpg")
try:
    with os.fdopen(fd, 'wb') as tmp_file:
        images[0].save(tmp_file.name, "JPEG")
    return temp_path
finally:
    # Cleanup w finally, nawet przy błędach
    if os.path.exists(temp_path):
        os.unlink(temp_path)
```

**Priorytet:** 🔴 **KRYTYCZNY** - Naprawić natychmiast

---

## ⚠️ WYSOKIE RYZYKO

### 3. Brak Walidacji Danych Wejściowych (DoS)

**Lokalizacja:** `llm.py:268-385`, `llm.py:388-525`

**Problem:**
```python
# llm.py:334-338
MAX_OCR_TEXT_LENGTH = 10000
if ocr_text and len(ocr_text) > MAX_OCR_TEXT_LENGTH:
    print(f"OSTRZEŻENIE: Tekst OCR jest za długi...")
    ocr_text = ocr_text[:MAX_OCR_TEXT_LENGTH] + "\n\n[... tekst OCR obcięty ...]"
```

**Ryzyko:**
- Brak walidacji rozmiaru obrazu przed przetwarzaniem
- Możliwość przekazania bardzo dużego obrazu (np. 1GB) powodującego:
  - Wyczerpanie pamięci
  - Zawieszenie aplikacji
  - Crash systemu
- Brak limitu czasu dla operacji OCR/LLM

**Rozwiązanie:**
```python
# Dodaj walidację przed przetwarzaniem
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_DIMENSIONS = (10000, 10000)  # Max szerokość/wysokość

def validate_image(image_path: str) -> None:
    """Waliduje obraz przed przetwarzaniem."""
    from PIL import Image
    
    # Sprawdź rozmiar pliku
    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_SIZE:
        raise ValueError(f"Obraz za duży: {file_size / 1024 / 1024:.2f} MB (max {MAX_IMAGE_SIZE / 1024 / 1024} MB)")
    
    # Sprawdź wymiary
    with Image.open(image_path) as img:
        width, height = img.size
        if width > MAX_IMAGE_DIMENSIONS[0] or height > MAX_IMAGE_DIMENSIONS[1]:
            raise ValueError(f"Obraz za duży: {width}x{height} (max {MAX_IMAGE_DIMENSIONS[0]}x{MAX_IMAGE_DIMENSIONS[1]})")
```

**Priorytet:** 🟠 **WYSOKIE** - Naprawić wkrótce

---

### 4. SQL Injection (Potencjalne)

**Lokalizacja:** `database.py`, `main.py:177-383`

**Status:** ✅ **BEZPIECZNE** - Używa SQLAlchemy ORM

**Analiza:**
- Kod używa SQLAlchemy ORM z parametrami, co zapobiega SQL injection
- Przykład bezpiecznego kodu:
```python
# main.py:286-289
alias = (
    session.query(AliasProduktu)
    .options(joinedload(AliasProduktu.produkt))
    .filter_by(nazwa_z_paragonu=raw_name)  # Bezpieczne - używa parametrów
    .first()
)
```

**Rekomendacja:**
- ✅ Kontynuować używanie ORM
- ⚠️ Upewnić się, że nigdzie nie używa się `session.execute()` z surowym SQL

**Priorytet:** 🟢 **NISKIE** - Monitorować

---

### 5. Niezabezpieczone Przechowywanie Danych

**Lokalizacja:** `database.py:12-14`

**Problem:**
```python
# database.py:12-14
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "data", "receipts.db")
DATABASE_URL = f"sqlite:///{db_path}"
```

**Ryzyko:**
- SQLite baza danych jest przechowywana w postaci niezaszyfrowanej
- Zawiera wrażliwe dane: ceny, daty zakupów, nazwy produktów
- W systemach wieloużytkownikowych: każdy użytkownik z dostępem do pliku może odczytać dane
- Brak szyfrowania na poziomie bazy danych

**Rozwiązanie:**
```python
# Opcja 1: Szyfrowanie na poziomie systemu plików (LUKS, VeraCrypt)
# Opcja 2: SQLCipher (szyfrowana wersja SQLite)
# Opcja 3: Szyfrowanie wrażliwych pól przed zapisem

from cryptography.fernet import Fernet
import base64
import os

class EncryptedDatabase:
    def __init__(self, db_path: str, encryption_key: bytes = None):
        if encryption_key is None:
            # Generuj klucz z hasła użytkownika lub pliku
            key_file = os.path.expanduser("~/.paragonocr_key")
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    encryption_key = f.read()
            else:
                encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    os.chmod(key_file, 0o600)  # Tylko właściciel
                    f.write(encryption_key)
        
        self.cipher = Fernet(encryption_key)
    
    def encrypt_field(self, value: str) -> str:
        """Szyfruje pole przed zapisem."""
        if value is None:
            return None
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_field(self, value: str) -> str:
        """Odszyfrowuje pole po odczycie."""
        if value is None:
            return None
        return self.cipher.decrypt(value.encode()).decode()
```

**Priorytet:** 🟠 **WYSOKIE** - Rozważyć dla produkcji

---

### 6. Logowanie Wrażliwych Danych

**Lokalizacja:** `main.py:96`, `llm.py:332-333`, `gui.py:1020`

**Problem:**
```python
# main.py:96
_call_log_callback(log_callback, f"--- WYNIK OCR (Tesseract) ---\n{full_ocr_text}\n-----------------------------")
# llm.py:332-333
print(f"INFO: Wysyłanie obrazu do modelu '{model_name}' (format=json)...")
print(f"INFO: Plik: {image_path}")  # Może zawierać wrażliwe ścieżki
```

**Ryzyko:**
- Logowanie pełnych ścieżek plików (może zawierać nazwy użytkowników)
- Logowanie zawartości OCR (może zawierać wrażliwe dane z paragonów)
- Logi mogą być dostępne dla innych użytkowników systemu
- W przypadku wycieku logów: możliwość odczytu danych użytkowników

**Rozwiązanie:**
```python
import logging
from pathlib import Path

def sanitize_path(path: str) -> str:
    """Usuwa wrażliwe informacje ze ścieżki."""
    p = Path(path)
    # Zwróć tylko nazwę pliku, nie pełną ścieżkę
    return p.name

def sanitize_log_message(message: str, max_length: int = 100) -> str:
    """Ogranicza długość wiadomości logowania."""
    if len(message) > max_length:
        return message[:max_length] + "... [obcięte]"
    return message

# W kodzie:
logger.info(f"INFO: Wysyłanie obrazu do modelu '{model_name}' (format=json)...")
logger.info(f"INFO: Plik: {sanitize_path(image_path)}")  # Tylko nazwa pliku

# Dla OCR - nie loguj pełnej zawartości
if len(full_ocr_text) > 200:
    logger.debug(f"OCR: {full_ocr_text[:200]}... [obcięte, długość: {len(full_ocr_text)}]")
else:
    logger.debug(f"OCR: {full_ocr_text}")
```

**Priorytet:** 🟠 **WYSOKIE** - Naprawić wkrótce

---

### 7. Brak Walidacji Modelu LLM

**Lokalizacja:** `main.py:434`, `llm.py:268-385`

**Problem:**
```python
# main.py:434
@click.option("--llm", "llm_model", required=True, type=str, help="Nazwa modelu LLM...")
def process(file_path: str, llm_model: str):
    # Brak walidacji czy model istnieje lub jest bezpieczny
```

**Ryzyko:**
- Użytkownik może przekazać dowolną nazwę modelu
- Brak walidacji czy model jest dozwolony
- Możliwość użycia niebezpiecznego modelu (jeśli dostępny lokalnie)
- Brak limitu czasu dla zapytań do LLM

**Rozwiązanie:**
```python
ALLOWED_LLM_MODELS = [
    "llava:latest",
    "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M",
    "mistral-ocr",
]

def validate_llm_model(model_name: str) -> str:
    """Waliduje nazwę modelu LLM."""
    if model_name not in ALLOWED_LLM_MODELS:
        raise ValueError(
            f"Model '{model_name}' nie jest dozwolony. "
            f"Dozwolone modele: {', '.join(ALLOWED_LLM_MODELS)}"
        )
    return model_name
```

**Priorytet:** 🟠 **WYSOKIE** - Naprawić wkrótce

---

## 🟡 ŚREDNIE RYZYKO

### 8. Brak Rate Limiting dla LLM

**Lokalizacja:** `llm.py:164-179`, `llm.py:340-359`

**Problem:**
- Brak ograniczenia liczby zapytań do LLM w jednostce czasu
- Możliwość wyczerpania zasobów (pamięć, CPU) przez wielokrotne zapytania

**Rozwiązanie:**
```python
from collections import deque
from time import time

class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def check(self) -> bool:
        """Sprawdza czy można wykonać zapytanie."""
        now = time()
        # Usuń stare zapytania
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True

# Użycie:
rate_limiter = RateLimiter(max_requests=10, time_window=60)
if not rate_limiter.check():
    raise Exception("Przekroczono limit zapytań do LLM. Spróbuj ponownie za chwilę.")
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 9. Brak Walidacji JSON z LLM

**Lokalizacja:** `llm.py:367-374`, `llm.py:511-515`

**Problem:**
```python
# llm.py:367-374
try:
    parsed_json = json.loads(raw_response_text)
except json.JSONDecodeError as e:
    print(f"BŁĄD: Model zwrócił niepoprawny JSON...")
    return None
```

**Ryzyko:**
- Brak walidacji struktury JSON przed użyciem
- Możliwość przekazania nieprawidłowych danych do bazy danych
- Brak walidacji typów danych (np. ujemne ceny, nieprawidłowe daty)

**Rozwiązanie:**
```python
from jsonschema import validate, ValidationError

RECEIPT_SCHEMA = {
    "type": "object",
    "required": ["sklep_info", "paragon_info", "pozycje"],
    "properties": {
        "sklep_info": {
            "type": "object",
            "required": ["nazwa"],
            "properties": {
                "nazwa": {"type": "string", "minLength": 1, "maxLength": 100},
                "lokalizacja": {"type": ["string", "null"], "maxLength": 200}
            }
        },
        "paragon_info": {
            "type": "object",
            "required": ["data_zakupu", "suma_calkowita"],
            "properties": {
                "data_zakupu": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}"},
                "suma_calkowita": {"type": "string", "pattern": r"^\d+\.\d{2}$"}
            }
        },
        "pozycje": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["nazwa_raw", "ilosc", "cena_calk"],
                "properties": {
                    "nazwa_raw": {"type": "string", "maxLength": 500},
                    "ilosc": {"type": ["string", "number"], "minimum": 0},
                    "cena_calk": {"type": ["string", "number"], "minimum": 0}
                }
            }
        }
    }
}

def validate_receipt_json(data: dict) -> dict:
    """Waliduje strukturę JSON paragonu."""
    try:
        validate(instance=data, schema=RECEIPT_SCHEMA)
        return data
    except ValidationError as e:
        raise ValueError(f"Nieprawidłowa struktura JSON: {e.message}")
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 10. Brak Timeout dla Operacji I/O

**Lokalizacja:** `llm.py:19-20`, `mistral_ocr.py:32-38`

**Problem:**
- Timeout jest ustawiony tylko dla Ollama (300s)
- Brak timeout dla operacji na plikach
- Brak timeout dla Mistral API

**Rozwiązanie:**
```python
# Dla Mistral API
import httpx

timeout = httpx.Timeout(30.0, connect=10.0)  # 30s timeout, 10s connect
client = Mistral(api_key=self.api_key, timeout=timeout)

# Dla operacji na plikach - użyj signal (Linux) lub threading.Timer
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operacja przekroczyła limit czasu")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 sekund
try:
    # Operacja na pliku
    pass
finally:
    signal.alarm(0)  # Wyłącz alarm
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 11. Brak Walidacji Danych z GUI

**Lokalizacja:** `gui.py:294-343`, `gui.py:898-942`

**Problem:**
```python
# gui.py:309-311
self.parsed_data["paragon_info"]["suma_calkowita"] = Decimal(
    self.total_entry.get().replace(",", ".")
)
# Brak walidacji czy to prawidłowa liczba
```

**Ryzyko:**
- Użytkownik może wprowadzić nieprawidłowe dane (np. ujemne ceny, nieprawidłowe daty)
- Możliwość zapisu nieprawidłowych danych do bazy

**Rozwiązanie:**
```python
def validate_decimal(value: str, min_value: Decimal = None, max_value: Decimal = None) -> Decimal:
    """Waliduje i konwertuje string na Decimal."""
    try:
        decimal_value = Decimal(value.replace(",", "."))
        if min_value is not None and decimal_value < min_value:
            raise ValueError(f"Wartość {decimal_value} jest mniejsza niż minimum {min_value}")
        if max_value is not None and decimal_value > max_value:
            raise ValueError(f"Wartość {decimal_value} jest większa niż maksimum {max_value}")
        return decimal_value
    except (ValueError, InvalidOperation) as e:
        raise ValueError(f"Nieprawidłowa wartość liczbowa: {value}") from e

# W kodzie:
try:
    suma = validate_decimal(
        self.total_entry.get(),
        min_value=Decimal("0.00"),
        max_value=Decimal("999999.99")
    )
    self.parsed_data["paragon_info"]["suma_calkowita"] = suma
except ValueError as e:
    messagebox.showerror("Błąd walidacji", str(e))
    return
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 12. Brak Szyfrowania Klucza API

**Lokalizacja:** `config.py:17`, `mistral_ocr.py:8`

**Problem:**
```python
# config.py:17
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
# Klucz API jest przechowywany w .env jako plaintext
```

**Ryzyko:**
- Klucz API jest przechowywany w pliku .env jako plaintext
- Jeśli plik .env zostanie skompromitowany, atakujący ma dostęp do API
- Brak rotacji kluczy

**Rozwiązanie:**
```python
# Opcja 1: Użyj systemowego keyring
import keyring

def get_api_key(service_name: str, username: str = "default") -> str:
    """Pobiera klucz API z systemowego keyring."""
    key = keyring.get_password(service_name, username)
    if key is None:
        # Fallback do zmiennej środowiskowej
        key = os.getenv(f"{service_name}_API_KEY", "")
        if key:
            # Zapisz w keyring dla przyszłości
            keyring.set_password(service_name, username, key)
    return key

# Opcja 2: Szyfrowanie pliku .env
from cryptography.fernet import Fernet

def load_encrypted_env(encrypted_file: str, key_file: str) -> dict:
    """Ładuje zaszyfrowany plik .env."""
    with open(key_file, 'rb') as f:
        key = f.read()
    cipher = Fernet(key)
    
    with open(encrypted_file, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted_data = cipher.decrypt(encrypted_data)
    # Parsuj jako .env
    return parse_env_string(decrypted_data.decode())
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 13. Brak Walidacji Rozmiaru Bazy Danych

**Lokalizacja:** `database.py:12-14`

**Problem:**
- Brak limitu rozmiaru bazy danych
- Możliwość wyczerpania miejsca na dysku przez złośliwe dane

**Rozwiązanie:**
```python
MAX_DB_SIZE = 1024 * 1024 * 1024  # 1 GB

def check_db_size(db_path: str) -> None:
    """Sprawdza rozmiar bazy danych."""
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        if size > MAX_DB_SIZE:
            raise ValueError(
                f"Baza danych przekroczyła limit rozmiaru: {size / 1024 / 1024:.2f} MB "
                f"(max {MAX_DB_SIZE / 1024 / 1024} MB)"
            )
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 14. Race Condition w Threading

**Lokalizacja:** `gui.py:1065-1101`, `gui.py:1150-1161`

**Problem:**
```python
# gui.py:1150-1161
thread = threading.Thread(
    target=run_processing_pipeline,
    args=(...),
)
thread.daemon = True
thread.start()
# Brak synchronizacji między wątkami
```

**Ryzyko:**
- Wielokrotne uruchomienie przetwarzania może prowadzić do konfliktów
- Race condition przy zapisie do bazy danych
- Możliwość uszkodzenia danych

**Rozwiązanie:**
```python
import threading

class ProcessingLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_processing = False
    
    def acquire(self) -> bool:
        """Próbuje zablokować przetwarzanie."""
        with self.lock:
            if self.is_processing:
                return False
            self.is_processing = True
            return True
    
    def release(self):
        """Zwolnij blokadę."""
        with self.lock:
            self.is_processing = False

# W kodzie:
processing_lock = ProcessingLock()

def start_processing(self):
    if not processing_lock.acquire():
        messagebox.showwarning("Uwaga", "Przetwarzanie już trwa. Poczekaj na zakończenie.")
        return
    
    try:
        # ... przetwarzanie ...
    finally:
        processing_lock.release()
```

**Priorytet:** 🟡 **ŚREDNIE**

---

### 15. Brak Cleanup przy Błędach

**Lokalizacja:** `main.py:130-132`, `ocr.py:22-43`

**Problem:**
```python
# main.py:130-132
if temp_image_path and os.path.exists(temp_image_path):
    os.remove(temp_image_path)
    # Tylko jeśli wszystko OK - jeśli wystąpi błąd wcześniej, plik pozostaje
```

**Rozwiązanie:**
```python
import atexit
import tempfile

class TempFileManager:
    def __init__(self):
        self.temp_files = []
        atexit.register(self.cleanup_all)
    
    def create_temp_file(self, suffix: str = ".jpg") -> str:
        """Tworzy plik tymczasowy i rejestruje go do cleanup."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self.temp_files.append(path)
        return path
    
    def cleanup(self, path: str):
        """Usuwa pojedynczy plik tymczasowy."""
        if path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
            self.temp_files.remove(path)
    
    def cleanup_all(self):
        """Usuwa wszystkie pliki tymczasowe."""
        for path in self.temp_files[:]:
            self.cleanup(path)

# Użycie:
temp_manager = TempFileManager()
temp_path = temp_manager.create_temp_file(".jpg")
try:
    # ... przetwarzanie ...
finally:
    temp_manager.cleanup(temp_path)
```

**Priorytet:** 🟡 **ŚREDNIE**

---

## 🟢 NISKIE RYZYKO

### 16. Brak Wersjonowania API

**Lokalizacja:** `llm.py`, `mistral_ocr.py`

**Rekomendacja:**
- Dodać wersjonowanie API dla przyszłych zmian
- Ułatwi to migrację i kompatybilność wsteczną

**Priorytet:** 🟢 **NISKIE**

---

### 17. Brak Audit Logging

**Lokalizacja:** Cały projekt

**Rekomendacja:**
- Dodać logowanie operacji na wrażliwych danych (kto, kiedy, co)
- Ułatwi to wykrycie nieautoryzowanego dostępu

**Priorytet:** 🟢 **NISKIE**

---

### 18. Brak Walidacji Wersji Zależności

**Lokalizacja:** `requirements.txt`

**Problem:**
- Brak pinowania wersji zależności
- Możliwość użycia niebezpiecznych wersji bibliotek

**Rozwiązanie:**
```txt
# requirements.txt - pinuj wersje
SQLAlchemy==2.0.23
click==8.1.7
python-dotenv==1.0.0
ollama==0.1.7
customtkinter==5.2.0
Pillow==10.1.0
pdf2image==1.16.3
pytesseract==0.3.10
mistralai==0.1.2
pytest==7.4.3
pytest-cov==4.1.0
rapidfuzz==3.5.2
```

**Priorytet:** 🟢 **NISKIE**

---

### 19. Brak CORS/CSRF Protection

**Lokalizacja:** N/A (Desktop app)

**Status:** ✅ **NIE DOTYCZY** - Aplikacja desktopowa, nie webowa

---

### 20. Brak Input Sanitization dla Wyświetlania

**Lokalizacja:** `gui.py:1080-1082`

**Problem:**
```python
# gui.py:1080-1082
self.log_textbox.insert("end", message + "\n")
# Brak sanitization - może zawierać znaki specjalne
```

**Ryzyko:**
- Niskie - aplikacja desktopowa
- Możliwość wyświetlenia nieprawidłowych znaków

**Rozwiązanie:**
```python
def sanitize_text(text: str) -> str:
    """Usuwa niebezpieczne znaki z tekstu."""
    # Usuń znaki kontrolne (oprócz \n, \t)
    import re
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text
```

**Priorytet:** 🟢 **NISKIE**

---

### 21. Brak Backup Bazy Danych

**Lokalizacja:** `database.py`

**Rekomendacja:**
- Dodać automatyczne backup bazy danych
- Chroni przed utratą danych

**Priorytet:** 🟢 **NISKIE**

---

## 📝 REKOMENDACJE

### Priorytet 1 (Krytyczne - Naprawić Natychmiast)

1. ✅ **Dodać walidację ścieżek plików** - zapobiega path traversal
2. ✅ **Zabezpieczyć pliki tymczasowe** - ustawić uprawnienia i użyć secure temp files

### Priorytet 2 (Wysokie - Naprawić Wkrótce)

3. ✅ **Dodać walidację rozmiaru plików** - zapobiega DoS
4. ✅ **Sanityzować logi** - usuń wrażliwe dane
5. ✅ **Walidować modele LLM** - tylko dozwolone modele
6. ✅ **Rozważyć szyfrowanie bazy danych** - dla produkcji

### Priorytet 3 (Średnie - Długoterminowe)

7. ✅ **Dodać rate limiting** - ochrona przed nadużyciami
8. ✅ **Walidować JSON z LLM** - użyć JSON Schema
9. ✅ **Dodać timeout dla wszystkich operacji I/O**
10. ✅ **Walidować dane z GUI** - przed zapisem do bazy
11. ✅ **Zabezpieczyć klucze API** - użyć keyring
12. ✅ **Dodać cleanup przy błędach** - użyć context managers

### Priorytet 4 (Niskie - Ulepszenia)

13. ✅ **Pinować wersje zależności** - bezpieczeństwo
14. ✅ **Dodać audit logging** - śledzenie operacji
15. ✅ **Dodać backup bazy danych** - ochrona danych

---

## 🔍 DODATKOWE UWAGI

### Pozytywne Aspekty Bezpieczeństwa

1. ✅ **Użycie SQLAlchemy ORM** - zapobiega SQL injection
2. ✅ **Separacja concerns** - łatwiejsze utrzymanie
3. ✅ **Obsługa błędów** - try/except w kluczowych miejscach
4. ✅ **Użycie zmiennych środowiskowych** - dla konfiguracji

### Zależności Bezpieczeństwa

- Sprawdź regularnie aktualizacje bezpieczeństwa dla:
  - `SQLAlchemy`
  - `Pillow` (znane podatności w przeszłości)
  - `pdf2image` (zależność od Poppler)
  - `pytesseract` (zależność od Tesseract)

### Testy Bezpieczeństwa

Rekomendowane testy:
1. **Fuzzing** - testowanie z nieprawidłowymi danymi wejściowymi
2. **Penetration testing** - testy penetracyjne
3. **Code review** - regularne przeglądy kodu
4. **Dependency scanning** - skanowanie zależności pod kątem podatności

---

## 📚 REFERENCJE

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security.html)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/core/engines.html#security)

---

**Koniec analizy bezpieczeństwa**

*Dokument wygenerowany automatycznie przez analizę kodu źródłowego.*

