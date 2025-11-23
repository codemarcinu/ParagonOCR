# 🔌 ParagonWeb API - Dokumentacja Techniczna

## Base URL
```
http://localhost:8000
```

## Uwierzytelnianie

Obecnie API nie wymaga uwierzytelniania (dla aplikacji self-hosted). W przyszłości można dodać:
- API Keys
- JWT Tokens
- OAuth2

## Format odpowiedzi

Wszystkie odpowiedzi są w formacie JSON. Błędy zwracają kod HTTP i obiekt z opisem:

```json
{
  "detail": "Opis błędu"
}
```

## Endpointy

### 1. Health Check

#### GET /
Sprawdza czy API działa.

**Response:**
```json
{
  "message": "ParagonWeb API",
  "version": "1.0.0"
}
```

---

### 2. Upload i Przetwarzanie Paragonów

#### POST /api/upload
Przetwarza przesłany paragon.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Body:**
  - `file` (file, required): Plik paragonu (PNG, JPG, JPEG, PDF)
  - Max size: 50MB

**Response 200:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

**Response 400:**
```json
{
  "detail": "Nieobsługiwany format pliku"
}
```

**Przykład (curl):**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@receipt.pdf"
```

**Przykład (Python):**
```python
import requests

with open('receipt.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f}
    )
    task_id = response.json()['task_id']
```

---

#### GET /api/task/{task_id}
Sprawdza status zadania przetwarzania.

**Path Parameters:**
- `task_id` (string, required): ID zadania zwrócone przez `/api/upload`

**Response 200:**
```json
{
  "status": "completed",
  "progress": 100,
  "message": "Przetwarzanie zakończone!",
  "file_path": "/app/uploads/550e8400-e29b-41d4-a716-446655440000.pdf"
}
```

**Statusy:**
- `processing` - W trakcie przetwarzania
- `completed` - Zakończone pomyślnie
- `error` - Błąd podczas przetwarzania

**Przykład (Python z polling):**
```python
import time
import requests

def wait_for_task(task_id, timeout=300):
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(f'http://localhost:8000/api/task/{task_id}')
        data = response.json()
        
        if data['status'] == 'completed':
            return data
        elif data['status'] == 'error':
            raise Exception(data['message'])
        
        time.sleep(2)  # Poll co 2 sekundy
    
    raise TimeoutError("Przetwarzanie przekroczyło limit czasu")
```

---

### 3. Paragony

#### GET /api/receipts
Zwraca listę paragonów.

**Query Parameters:**
- `skip` (int, optional, default: 0): Liczba paragonów do pominięcia (paginacja)
- `limit` (int, optional, default: 50): Maksymalna liczba paragonów

**Response 200:**
```json
{
  "receipts": [
    {
      "paragon_id": 1,
      "sklep": "Lidl",
      "data_zakupu": "2025-01-15",
      "suma_paragonu": 123.45,
      "liczba_pozycji": 10,
      "plik_zrodlowy": "/path/to/receipt.pdf"
    },
    {
      "paragon_id": 2,
      "sklep": "Biedronka",
      "data_zakupu": "2025-01-14",
      "suma_paragonu": 89.99,
      "liczba_pozycji": 8,
      "plik_zrodlowy": "/path/to/receipt2.jpg"
    }
  ],
  "total": 2
}
```

**Przykład:**
```bash
curl "http://localhost:8000/api/receipts?skip=0&limit=10"
```

---

### 4. Statystyki

#### GET /api/stats
Zwraca szczegółowe statystyki zakupów.

**Response 200:**
```json
{
  "total_statistics": {
    "total_receipts": 50,
    "total_spent": 5000.00,
    "total_items": 500,
    "avg_receipt": 100.00
  },
  "by_store": [
    {
      "name": "Lidl",
      "amount": 2000.00
    },
    {
      "name": "Biedronka",
      "amount": 1500.00
    }
  ],
  "by_category": [
    {
      "name": "Nabiał",
      "amount": 500.00
    },
    {
      "name": "Warzywa",
      "amount": 400.00
    }
  ],
  "top_products": [
    {
      "name": "Mleko",
      "count": 20,
      "total": 200.00
    },
    {
      "name": "Chleb",
      "count": 15,
      "total": 150.00
    }
  ],
  "monthly": [
    {
      "month": "Styczeń 2025",
      "receipts": 10,
      "spent": 1000.00
    },
    {
      "month": "Grudzień 2024",
      "receipts": 8,
      "spent": 800.00
    }
  ]
}
```

**Przykład:**
```python
import requests

response = requests.get('http://localhost:8000/api/stats')
stats = response.json()

print(f"Łączne wydatki: {stats['total_statistics']['total_spent']} PLN")
print(f"Średnia wartość paragonu: {stats['total_statistics']['avg_receipt']} PLN")
```

---

### 5. Magazyn

#### GET /api/inventory
Zwraca aktualny stan magazynu.

**Response 200:**
```json
{
  "inventory": [
    {
      "produkt_id": 1,
      "nazwa": "Mleko",
      "ilosc": 2.0,
      "jednostka": "l",
      "data_waznosci": "2025-01-20",
      "zamrozone": false,
      "kategoria": "Nabiał"
    },
    {
      "produkt_id": 2,
      "nazwa": "Chleb",
      "ilosc": 1.0,
      "jednostka": "szt",
      "data_waznosci": null,
      "zamrozone": false,
      "kategoria": "Pieczywo"
    }
  ]
}
```

**Przykład:**
```python
import requests
from datetime import datetime, date

response = requests.get('http://localhost:8000/api/inventory')
inventory = response.json()['inventory']

# Znajdź produkty przeterminowane
today = date.today()
expired = [
    item for item in inventory
    if item['data_waznosci'] and datetime.fromisoformat(item['data_waznosci']).date() < today
]

print(f"Przeterminowane produkty: {len(expired)}")
```

---

### 6. Czat z Bielikiem

#### POST /api/chat
Wysyła wiadomość do asystenta kulinarnego Bielik.

**Request:**
```json
{
  "question": "Co mam do jedzenia?"
}
```

**Response 200:**
```json
{
  "answer": "Masz w magazynie: mleko (2l), chleb (1szt), jajka (10szt). Możesz przygotować jajecznicę, kanapki lub omlet."
}
```

**Response 500:**
```json
{
  "detail": "Błąd podczas komunikacji z Bielikiem: ..."
}
```

**Przykłady pytań:**
- "Co mam do jedzenia?"
- "Co mogę zrobić na obiad?"
- "Czy mam mleko w magazynie?"
- "Jakie potrawy mogę przygotować z dostępnych produktów?"
- "Wygeneruj listę zakupów na obiad"

**Przykład:**
```python
import requests

questions = [
    "Co mam do jedzenia?",
    "Co mogę zrobić na obiad?",
    "Wygeneruj listę zakupów na spaghetti"
]

for question in questions:
    response = requests.post(
        'http://localhost:8000/api/chat',
        json={'question': question}
    )
    answer = response.json()['answer']
    print(f"Pytanie: {question}")
    print(f"Odpowiedź: {answer}\n")
```

---

### 7. Ustawienia

#### GET /api/settings
Zwraca aktualne ustawienia aplikacji.

**Response 200:**
```json
{
  "use_cloud_ai": true,
  "use_cloud_ocr": true,
  "openai_api_key_set": true,
  "mistral_api_key_set": true
}
```

**Uwaga:** `openai_api_key_set` i `mistral_api_key_set` zwracają tylko informację czy klucz jest ustawiony (true/false), nie zwracają wartości klucza ze względów bezpieczeństwa.

---

#### POST /api/settings
Aktualizuje ustawienia aplikacji.

**Request:**
```json
{
  "use_cloud_ai": true,
  "use_cloud_ocr": true,
  "openai_api_key": "sk-...",
  "mistral_api_key": "..."
}
```

**Wszystkie pola są opcjonalne** - możesz zaktualizować tylko wybrane.

**Response 200:**
```json
{
  "message": "Ustawienia zaktualizowane"
}
```

**Przykład:**
```python
import requests

# Przełącz na tryb lokalny
response = requests.post(
    'http://localhost:8000/api/settings',
    json={
        "use_cloud_ai": False,
        "use_cloud_ocr": False
    }
)
print(response.json()['message'])
```

---

## Kody błędów HTTP

- `200 OK` - Sukces
- `400 Bad Request` - Nieprawidłowe żądanie (np. zły format pliku)
- `404 Not Found` - Zasób nie znaleziony (np. nieistniejące task_id)
- `500 Internal Server Error` - Błąd serwera

## Rate Limiting

Obecnie brak limitów. W przyszłości można dodać:
- Limit requestów na minutę
- Limit uploadów na godzinę

## Webhooks (Przyszłość)

Planowane webhooki dla:
- Zakończenie przetwarzania paragonu
- Nowy produkt w magazynie
- Przeterminowany produkt

## Przykłady integracji

### Python SDK (Przyszłość)

```python
from paragonweb import ParagonWebClient

client = ParagonWebClient(api_url="http://localhost:8000")

# Upload paragonu
task = client.upload_receipt("receipt.pdf")
task.wait_for_completion()

# Pobierz statystyki
stats = client.get_stats()
print(f"Wydatki: {stats.total_spent} PLN")

# Zapytaj Bielika
answer = client.chat("Co mam do jedzenia?")
print(answer)
```

### JavaScript/TypeScript

```typescript
const API_URL = 'http://localhost:8000';

async function uploadReceipt(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_URL}/api/upload`, {
    method: 'POST',
    body: formData
  });
  
  const { task_id } = await response.json();
  return task_id;
}

async function getTaskStatus(taskId: string) {
  const response = await fetch(`${API_URL}/api/task/${taskId}`);
  return await response.json();
}
```

---

**Wersja API:** 1.0.0  
**Ostatnia aktualizacja:** 2025-01-XX

