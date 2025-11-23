# 💡 ParagonWeb - Przykłady Użycia

## Spis treści

1. [Podstawowe użycie](#podstawowe-użycie)
2. [API Examples](#api-examples)
3. [Integracje](#integracje)
4. [Scenariusze użycia](#scenariusze-użycia)

---

## Podstawowe użycie

### 1. Dodanie paragonu przez UI

1. Otwórz http://localhost:8080
2. Kliknij "Wybierz plik paragonu"
3. Wybierz plik (PNG, JPG, PDF)
4. Plik zostanie automatycznie przesłany i przetworzony
5. Postęp jest widoczny na pasku postępu

### 2. Sprawdzenie magazynu

1. Przejdź do zakładki "Magazyn"
2. Zobacz listę wszystkich produktów
3. Filtruj po kategorii lub dacie ważności
4. Sprawdź status produktów (OK, Wkrótce przeterminowany, Przeterminowany)

### 3. Rozmowa z Bielikiem

1. Przejdź do zakładki "Bielik"
2. Zadaj pytanie, np.:
   - "Co mam do jedzenia?"
   - "Co mogę zrobić na obiad?"
   - "Wygeneruj listę zakupów na spaghetti"
3. Bielik odpowie na podstawie dostępnych produktów w magazynie

---

## API Examples

### Python

#### Upload paragonu

```python
import requests
import time

def upload_receipt(file_path):
    """Przesyła paragon i czeka na zakończenie przetwarzania."""
    
    # Upload
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/upload',
            files={'file': f}
        )
        response.raise_for_status()
        task_id = response.json()['task_id']
        print(f"Zadanie utworzone: {task_id}")
    
    # Czekaj na zakończenie
    while True:
        response = requests.get(f'http://localhost:8000/api/task/{task_id}')
        data = response.json()
        
        print(f"Status: {data['status']}, Postęp: {data['progress']}%")
        
        if data['status'] == 'completed':
            print("Przetwarzanie zakończone!")
            return task_id
        elif data['status'] == 'error':
            raise Exception(f"Błąd: {data['message']}")
        
        time.sleep(2)

# Użycie
upload_receipt('receipt.pdf')
```

#### Pobranie statystyk

```python
import requests
from datetime import datetime

def get_monthly_spending():
    """Pobiera wydatki miesięczne."""
    response = requests.get('http://localhost:8000/api/stats')
    stats = response.json()
    
    print("=== Statystyki ===")
    print(f"Łączne paragony: {stats['total_statistics']['total_receipts']}")
    print(f"Łączne wydatki: {stats['total_statistics']['total_spent']:.2f} PLN")
    print(f"Średnia wartość paragonu: {stats['total_statistics']['avg_receipt']:.2f} PLN")
    
    print("\n=== Wydatki miesięczne ===")
    for month in stats['monthly']:
        print(f"{month['month']}: {month['spent']:.2f} PLN ({month['receipts']} paragonów)")
    
    print("\n=== Top sklepy ===")
    for store in stats['by_store'][:5]:
        print(f"{store['name']}: {store['amount']:.2f} PLN")
    
    print("\n=== Top kategorie ===")
    for cat in stats['by_category'][:5]:
        print(f"{cat['name']}: {cat['amount']:.2f} PLN")

get_monthly_spending()
```

#### Sprawdzenie magazynu

```python
import requests
from datetime import datetime, date

def check_expiring_products(days=3):
    """Sprawdza produkty, które wkrótce się przeterminują."""
    response = requests.get('http://localhost:8000/api/inventory')
    inventory = response.json()['inventory']
    
    today = date.today()
    threshold = today.replace(day=today.day + days)
    
    expiring = []
    for item in inventory:
        if item['data_waznosci']:
            expiry_date = datetime.fromisoformat(item['data_waznosci']).date()
            if today <= expiry_date <= threshold:
                expiring.append(item)
    
    if expiring:
        print(f"Produkty przeterminowujące się w ciągu {days} dni:")
        for item in expiring:
            print(f"  - {item['nazwa']}: {item['ilosc']} {item['jednostka']} (ważność: {item['data_waznosci']})")
    else:
        print("Brak produktów przeterminowujących się w najbliższym czasie.")
    
    return expiring

check_expiring_products()
```

#### Rozmowa z Bielikiem

```python
import requests

def ask_bielik(question):
    """Zadaje pytanie Bielikowi."""
    response = requests.post(
        'http://localhost:8000/api/chat',
        json={'question': question}
    )
    response.raise_for_status()
    return response.json()['answer']

# Przykłady pytań
questions = [
    "Co mam do jedzenia?",
    "Co mogę zrobić na obiad?",
    "Czy mam mleko w magazynie?",
    "Jakie potrawy mogę przygotować z dostępnych produktów?",
    "Wygeneruj listę zakupów na spaghetti",
]

for question in questions:
    print(f"\n❓ Pytanie: {question}")
    answer = ask_bielik(question)
    print(f"🦅 Bielik: {answer}")
```

### JavaScript/TypeScript

#### Upload paragonu

```typescript
async function uploadReceipt(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/api/upload', {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.task_id;
}

async function waitForTask(taskId: string): Promise<void> {
  while (true) {
    const response = await fetch(`http://localhost:8000/api/task/${taskId}`);
    const data = await response.json();
    
    console.log(`Status: ${data.status}, Progress: ${data.progress}%`);
    
    if (data.status === 'completed') {
      console.log('Processing completed!');
      return;
    } else if (data.status === 'error') {
      throw new Error(data.message);
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// Użycie
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file) {
    const taskId = await uploadReceipt(file);
    await waitForTask(taskId);
  }
});
```

#### Pobranie statystyk

```typescript
async function getStats() {
  const response = await fetch('http://localhost:8000/api/stats');
  const stats = await response.json();
  
  console.log('Total spent:', stats.total_statistics.total_spent);
  console.log('Top stores:', stats.by_store);
  console.log('Top categories:', stats.by_category);
  
  return stats;
}
```

### cURL

#### Upload paragonu

```bash
# Upload
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@receipt.pdf"

# Sprawdź status
curl "http://localhost:8000/api/task/{task_id}"
```

#### Pobranie statystyk

```bash
curl "http://localhost:8000/api/stats" | jq
```

#### Rozmowa z Bielikiem

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Co mam do jedzenia?"}'
```

---

## Integracje

### Home Assistant

```yaml
# configuration.yaml
rest:
  - resource: http://localhost:8000/api/inventory
    scan_interval: 3600
    sensor:
      - name: "ParagonWeb Inventory"
        value_template: "{{ value_json.inventory | length }}"
        json_attributes:
          - inventory
```

### Zapier / Make.com

**Trigger:** Nowy paragon
- Webhook: `POST /api/upload`
- Action: Zapisz do Google Sheets / Notion

**Action:** Sprawdź magazyn
- Webhook: `GET /api/inventory`
- Formatuj i wyślij email

### IFTTT

**Applet:** "Jeśli nowy email z paragonem, to dodaj do ParagonWeb"
- Trigger: Email z załącznikiem
- Action: Upload do `/api/upload`

---

## Scenariusze użycia

### Scenariusz 1: Codzienne zakupy

1. **Po zakupach:**
   - Zrób zdjęcie paragonu telefonem
   - Prześlij przez UI lub API
   - System automatycznie przetworzy i doda do magazynu

2. **Sprawdzenie magazynu:**
   - Otwórz zakładkę "Magazyn"
   - Zobacz co masz w domu
   - Sprawdź daty ważności

3. **Planowanie posiłków:**
   - Zapytaj Bielika: "Co mogę zrobić na obiad?"
   - Otrzymaj propozycje potraw
   - Wygeneruj listę zakupów dla brakujących produktów

### Scenariusz 2: Analiza wydatków

1. **Miesięczny przegląd:**
   - Otwórz Dashboard
   - Zobacz statystyki wydatków
   - Sprawdź trendy miesięczne

2. **Analiza kategorii:**
   - Zobacz wydatki według kategorii
   - Zidentyfikuj obszary do oszczędności
   - Porównaj miesiące

3. **Eksport danych:**
   - Użyj API do pobrania danych
   - Zaimportuj do Excel/Google Sheets
   - Utwórz własne wykresy

### Scenariusz 3: Automatyzacja

1. **Automatyczny upload:**
   - Skonfiguruj webhook w aplikacji sklepu
   - Paragony automatycznie trafiają do systemu
   - Otrzymuj powiadomienia o nowych produktach

2. **Alerty o przeterminowaniu:**
   - Skrypt sprawdza magazyn codziennie
   - Wysyła email/SMS o produktach przeterminowujących się
   - Sugeruje potrawy do przygotowania

3. **Integracja z listą zakupów:**
   - Bielik generuje listę zakupów
   - Automatycznie dodaje do aplikacji zakupowej
   - Oznacza produkty już dostępne w magazynie

### Scenariusz 4: Współdzielony magazyn

1. **Wielu użytkowników:**
   - Każdy dodaje swoje paragony
   - Wspólny magazyn
   - Wspólne statystyki

2. **Planowanie posiłków:**
   - Bielik widzi wszystkie produkty
   - Sugeruje potrawy dla całej rodziny
   - Generuje listy zakupów

---

## Zaawansowane przykłady

### Batch processing

```python
import os
import requests
from pathlib import Path

def process_directory(directory):
    """Przetwarza wszystkie paragony w katalogu."""
    directory = Path(directory)
    files = list(directory.glob('*.pdf')) + list(directory.glob('*.jpg')) + list(directory.glob('*.png'))
    
    results = []
    for file in files:
        try:
            print(f"Przetwarzanie {file.name}...")
            task_id = upload_receipt(str(file))
            results.append({'file': file.name, 'task_id': task_id, 'status': 'success'})
        except Exception as e:
            print(f"Błąd przy {file.name}: {e}")
            results.append({'file': file.name, 'status': 'error', 'error': str(e)})
    
    return results

# Użycie
results = process_directory('./paragony')
```

### Monitoring i alerty

```python
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

def check_expiring_and_alert():
    """Sprawdza przeterminowujące się produkty i wysyła alert."""
    response = requests.get('http://localhost:8000/api/inventory')
    inventory = response.json()['inventory']
    
    today = date.today()
    expiring = [
        item for item in inventory
        if item['data_waznosci'] and 
        datetime.fromisoformat(item['data_waznosci']).date() <= today.replace(day=today.day + 3)
    ]
    
    if expiring:
        message = "Produkty przeterminowujące się:\n\n"
        for item in expiring:
            message += f"- {item['nazwa']}: {item['ilosc']} {item['jednostka']} (ważność: {item['data_waznosci']})\n"
        
        # Wyślij email (konfiguracja SMTP)
        send_email("Alert: Produkty przeterminowujące się", message)
    
    return expiring

def send_email(subject, body):
    """Wysyła email (wymaga konfiguracji SMTP)."""
    # Implementacja wysyłki email
    pass
```

---

**Więcej przykładów:** Zobacz [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

