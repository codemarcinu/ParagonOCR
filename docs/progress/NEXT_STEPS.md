# Kolejne Kroki - ParagonOCR Web Edition

## 🎯 Priorytet 1: Testowanie i Uruchomienie Phase 1 MVP

### 1.1 Przygotowanie środowiska

```bash
# 1. Backend - utwórz virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Utwórz plik .env (skopiuj z .env.example jeśli istnieje)
# Lub utwórz ręcznie z konfiguracją:
cat > .env << EOF
OLLAMA_HOST=http://localhost:11434
TEXT_MODEL=bielik-4.5b-v3.0-instruct:Q4_K_M
OCR_ENGINE=tesseract
DATABASE_URL=sqlite:///./data/receipts.db
UPLOAD_DIR=./data/uploads
EOF

# 4. Utwórz katalogi
mkdir -p data/uploads

# 5. Uruchom migracje bazy danych
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# 6. Uruchom backend
uvicorn app.main:app --reload
```

```bash
# 1. Frontend - zainstaluj zależności
cd frontend
npm install

# 2. Uruchom dev server
npm run dev
```

### 1.2 Weryfikacja wymagań

- [ ] **Ollama działa i model Bielik jest dostępny:**
  ```bash
  ollama serve  # W osobnym terminalu
  ollama list   # Sprawdź czy bielik-4.5b-v3.0-instruct jest dostępny
  ```

- [ ] **Tesseract OCR zainstalowany:**
  ```bash
  tesseract --version
  ```

- [ ] **Backend odpowiada:**
  ```bash
  curl http://localhost:8000/health
  # Powinno zwrócić: {"status": "healthy"}
  ```

- [ ] **Frontend działa:**
  - Otwórz http://localhost:5173
  - Powinien wyświetlić się Dashboard

### 1.3 Testowanie podstawowego flow

1. **Test uploadu paragonu:**
   - Przeciągnij plik PDF/PNG na obszar uploadu
   - Sprawdź czy pojawia się progress indicator
   - Sprawdź czy paragon pojawia się w liście

2. **Test przetwarzania:**
   - Sprawdź logi backendu (czy OCR działa)
   - Sprawdź czy LLM parsuje poprawnie
   - Sprawdź czy dane są zapisywane w bazie

3. **Test wyświetlania:**
   - Kliknij na paragon w liście
   - Sprawdź czy ReceiptViewer wyświetla dane poprawnie

## 🔧 Priorytet 2: Naprawienie i Ulepszenie Phase 1

### 2.1 Naprawienie znanych problemów

- [ ] **WebSocket dla real-time progress:**
  - Obecnie progress jest symulowany
  - Zaimplementuj prawdziwy WebSocket w `process_receipt_async`
  - Połącz frontend z WebSocket endpoint

- [ ] **Obsługa błędów:**
  - Dodaj lepsze komunikaty błędów w UI
  - Dodaj retry logic dla failed uploads
  - Dodaj walidację plików po stronie frontendu

- [ ] **Database migrations:**
  - Utwórz pierwszą migrację Alembic
  - Sprawdź czy wszystkie modele są poprawnie zdefiniowane

### 2.2 Ulepszenia UX

- [ ] **Receipt Viewer:**
  - Dodaj możliwość edycji pozycji
  - Dodaj możliwość przypisania produktu do kategorii
  - Dodaj wyświetlanie obrazu paragonu (jeśli dostępny)

- [ ] **Dashboard:**
  - Dodaj filtrowanie paragonów (po dacie, sklepie)
  - Dodaj paginację dla długich list
  - Dodaj sortowanie

- [ ] **Loading states:**
  - Dodaj skeleton loaders
  - Popraw wskaźniki ładowania

## 📊 Priorytet 3: Przygotowanie do Phase 2

### 3.1 Analytics Service (Backend)

```python
# backend/app/services/analytics_service.py
- spending_by_category(period)
- spending_by_shop(period)
- average_product_price(product_name)
- purchase_frequency(product_name)
- budget_status()
```

**Zadania:**
- [ ] Utwórz `analytics_service.py`
- [ ] Dodaj endpoint `/api/analytics/spending`
- [ ] Dodaj endpoint `/api/analytics/categories`
- [ ] Dodaj endpoint `/api/analytics/trends`

### 3.2 RAG Engine (Backend)

```python
# backend/app/services/rag_service.py
- build_vector_store()  # Sentence transformers
- semantic_search(query, top_k=5)
- format_context_for_llm(context)
```

**Zadania:**
- [ ] Zainstaluj `sentence-transformers`
- [ ] Utwórz `rag_service.py`
- [ ] Zaimplementuj embedding generation
- [ ] Zaimplementuj semantic search
- [ ] Dodaj cache dla embeddings

### 3.3 Frontend - Analytics Page

- [ ] Utwórz `pages/Analytics.tsx`
- [ ] Dodaj komponenty wykresów (recharts lub chart.js)
- [ ] Dodaj `store/analyticsStore.ts`
- [ ] Dodaj routing (React Router)

### 3.4 Frontend - Chat Interface

- [ ] Utwórz `pages/Chat.tsx`
- [ ] Utwórz `components/ChatUI.tsx`
- [ ] Dodaj `store/chatStore.ts`
- [ ] Zaimplementuj streaming responses
- [ ] Dodaj RAG context display

## 🚀 Priorytet 4: Phase 2 Implementation

### 4.1 Analytics Dashboard (Week 3)

**Backend:**
- [ ] Analytics service
- [ ] Analytics router
- [ ] Testy jednostkowe

**Frontend:**
- [ ] Analytics page
- [ ] Wykresy (spending trends, category breakdown)
- [ ] Filtry (date range, shop, category)

### 4.2 RAG Engine (Week 3-4)

**Backend:**
- [ ] RAG service
- [ ] Embedding generation
- [ ] Semantic search
- [ ] Context formatting

**Frontend:**
- [ ] Chat interface
- [ ] RAG context display
- [ ] Conversation history

### 4.3 Product Management (Week 4)

**Backend:**
- [ ] Products router
- [ ] Product search
- [ ] Price history tracking

**Frontend:**
- [ ] Products page
- [ ] Product search component
- [ ] Price history charts

## 📝 Priorytet 5: Dokumentacja i Testy

### 5.1 Dokumentacja

- [ ] API documentation (Swagger/OpenAPI)
- [ ] User guide
- [ ] Developer guide
- [ ] Deployment guide

### 5.2 Testy

- [ ] Backend unit tests (pytest)
- [ ] Frontend component tests (Vitest)
- [ ] Integration tests
- [ ] E2E tests (Playwright)

## 🎨 Priorytet 6: Polish & Optimization

### 6.1 Performance

- [ ] Lazy loading dla komponentów
- [ ] Virtual scrolling dla długich list
- [ ] Image optimization
- [ ] Database query optimization

### 6.2 UI/UX Improvements

- [ ] Dark mode toggle
- [ ] Responsive design improvements
- [ ] Accessibility (a11y)
- [ ] Animations & transitions

## 📋 Checklist - Co zrobić teraz

### Natychmiast (dzisiaj):

1. ✅ **Uruchom backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # Utwórz .env
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

2. ✅ **Uruchom frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. ✅ **Przetestuj podstawowy flow:**
   - Upload paragonu
   - Sprawdź czy przetwarza się poprawnie
   - Sprawdź czy wyświetla się w dashboardzie

### Ten tydzień:

4. ⏳ **Napraw WebSocket dla real-time progress**
5. ⏳ **Dodaj pierwszą migrację Alembic**
6. ⏳ **Popraw obsługę błędów**
7. ⏳ **Dodaj edycję pozycji w ReceiptViewer**

### Następny tydzień (Phase 2):

8. ⏳ **Zaimplementuj Analytics Service**
9. ⏳ **Zaimplementuj RAG Engine**
10. ⏳ **Utwórz Chat Interface**

## 🔗 Przydatne linki

- FastAPI docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Ollama: http://localhost:11434

## 💡 Wskazówki

1. **Zacznij od testowania Phase 1** - upewnij się, że wszystko działa
2. **Napraw błędy przed Phase 2** - solidne fundamenty są ważne
3. **Testuj na prawdziwych paragonach** - użyj przykładowych plików z `paragony/`
4. **Monitoruj logi** - backend i frontend logują ważne informacje
5. **Używaj Swagger UI** - `/docs` endpoint do testowania API

---

**Status:** Phase 1 MVP ✅ | Phase 2 ⏳ | Phase 3 ⏳

