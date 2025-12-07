# ParagonOCR Web Edition - Mapa Wdrożenia

Kompletna mapa architektury, aktualnego statusu wdrożenia oraz planowanych prac dla projektu ParagonOCR Web Edition.

## 1. Architektura Systemu

### Backend (API)
- **Framework**: FastAPI (Python 3.10+)
- **Baza Danych**: SQLite (lokalnie) / PostgreSQL (produkcyjnie) + SQLAlchemy ORM (alembic do migracji).
- **Struktura**: Modułowa (`routers`, `services`, `models`, `schemas`).
- **Autentykacja**: OAuth2 z tokenami JWT.
- **AI/OCR**: Hybrydowe podejście:
    - **OCR**: Tesseract (lokalnie) lub Mistral OCR (cloud).
    - **LLM**: Ollama (lokalnie - Bielik/Mistral) lub OpenAI API.

### Frontend (UI)
- **Framework**: React 19 + Vite.
- **Styling**: TailwindCSS.
- **State Management**: Zustand (Auth, Chat, Receipts).
- **Komponenty**: Własne + Lucide Icons + Recharts (wykresy).
- **Routing**: React Router v7 z zabezpieczeniem (`ProtectedRoute`).

## 2. Status Wdrożenia

### ✅ Zrealizowane Moduły

#### 🔒 Bezpieczeństwo i Autentykacja
- [x] Pełny system logowania i rejestracji (JWT).
- [x] Zabezpieczenie wszystkich endpointów API (`get_current_user`).
- [x] Frontend: Przechowywanie sesji, interceptory zapytań (automatyczne dodawanie tokena).
- [x] Walidacja danych wejściowych (Schema Pydantic) - zapobieganie błędom i atakom.
- [x] Rate Limiting - ochrona przed spamem/brute-force (custom handler 429).

#### 🧾 Paragony (Receipts)
- [x] Upload plików (PDF/Image).
- [x] Przetwarzanie asynchroniczne (OCR -> LLM -> DB).
- [x] WebSocket: Podgląd postępu przetwarzania w czasie rzeczywistym.
- [x] Lista paragonów z filtrowaniem i sortowaniem.
- [x] Szczegóły paragonu z edycją pozycji.

#### 🛒 Produkty i Asystent (Products & Chat)
- [x] Baza produktów z normalizacją nazw.
- [x] Historia cen produktów.
- [x] Czat z AI (RAG) - kontekstowa rozmowa o wydatkach.
- [x] Zarządzanie historią konwersacji.

#### 📊 Analityka (Analytics)
- [x] Dashboard z podsumowaniem wydatków.
- [x] Wykresy: Trendy dzienne, podział na kategorie, sklepy.

### 🚧 Do Zrobienia (Roadmapa)

#### Faza 1: Stabilizacja i Docker (Priorytet)
1.  **Aktualizacja Docker Compose**: Obecny plik `docker-compose.yml` odnosi się do starej wersji NiceGUI. Należy go przepisać pod nowy stack (React + FastAPI).
2.  **Testy**: Dodać testy integracyjne (Pytest) i jednostkowe (Vitest).

#### Faza 2: Advanced Features
1.  **Zaawansowana Analityka**: Regresja liniowa do prognozy wydatków, wykrywanie anomalii cenowych.
2.  **Multitenancy / Rodzina**: Współdzielenie paragonów i budżetów między użytkownikami.
3.  **Wersja Mobilna (PWA)**: Optymalizacja pod ekrany dotykowe i instalacja jako aplikacja.

## 3. Instrukcja Uruchomienia (Deweloperska)

### Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```
Dostępny pod: `http://localhost:8000`
Dokumentacja API: `http://localhost:8000/docs`

### Frontend
```bash
cd frontend
npm run dev
```
Dostępny pod: `http://localhost:5173`

## 4. Struktura Projektu

```plaintext
/ParagonOCR
├── backend/
│   ├── app/
│   │   ├── models/       # Modele DB (SQLAlchemy)
│   │   ├── routers/      # Endpointy API
│   │   ├── schemas/      # Schematy Pydantic (Walidacja)
│   │   ├── services/     # Logika biznesowa (OCR, LLM, Auth)
│   │   └── main.py       # Punkt wejścia aplikacji
│   └── alembic/          # Migracje bazy danych
├── frontend/
│   ├── src/
│   │   ├── components/   # Reużywalne komponenty UI
│   │   ├── pages/        # Widoki aplikacji (Login, Dashboard...)
│   │   ├── store/        # Stan aplikacji (Zustand)
│   │   └── lib/          # Klient API (Axios)
│   └── package.json
├── IMPLEMENTATION_MAP.md # Ten plik
└── task.md               # Szczegółowa lista zadań
```
