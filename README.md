# 🧾 ParagonOCR Web Edition

**ParagonOCR Web Edition** to nowoczesna, pełnowymiarowa aplikacja webowa typu full-stack, stworzona do cyfryzacji paragonów, zarządzania domowym budżetem oraz inteligentnego planowania posiłków (AI Meal Planning). System wykorzystuje zaawansowane technologie: FastAPI, React 19 oraz lokalne modele sztucznej inteligencji (Ollama + Tesseract), zapewniając prywatność i niezależność od chmury.

[![Version](https://img.shields.io/badge/version-1.0.0--beta-blue)](https://github.com/codemarcinu/paragonocr)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![React](https://img.shields.io/badge/react-19.2-blue)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🎯 Przeznaczenie Aplikacji

Głównym celem ParagonOCR jest **automatyzacja i optymalizacja zarządzania domowymi zasobami**. Aplikacja rozwiązuje codzienne problemy związane z:
1.  **Gromadzeniem papierowych paragonów** – cyfryzacja i łatwe wyszukiwanie.
2.  **Śledzeniem wydatków** – automatyczna kategoryzacja i analiza kosztów.
3.  **Marnowaniem żywności** – monitorowanie terminów ważności i sugerowanie przepisów z posiadanych produktów (Zero Waste).
4.  **Planowaniem zakupów** – inteligentne listy zakupów oparte na rzeczywistym zużyciu i planowanych posiłkach.

Dzięki wykorzystaniu **lokalnych modeli LLM (np. Bielik)**, Twoje dane finansowe i osobiste nigdy nie opuszczają Twojego komputera, gwarantując **100% prywatności**.

---

## ✨ Kluczowe Funkcjonalności

### 📄 Przetwarzanie Paragonów (OCR & AI)
- **Wieloczęściowy Pipeline:** Upload (PDF/IMG) -> OCR (Tesseract) -> Normalizacja -> AI Parsing (Ollama).
- **Czyszczenie Danych:** Automatyczna korekta błędów OCR, mapowanie nazw produktów (np. "MLEKO 3.2%" -> "Mleko") i rozpoznawanie sklepów.
- **Czas Rzeczywisty:** Podgląd postępu przetwarzania dzięki WebSocket.

### 🤖 Inteligentny Asystent AI (RAG)
Wbudowany czat z modelem językowym, który ma dostęp do Twojej bazy produktów ("Retrieval-Augmented Generation"):
- **Zapytania o zapasy:** "Co mam w lodówce?", "Czy mam składniki na pizzę?".
- **Kulinarny Doradca:** "Co ugotować z produktów, które zaraz się przeterminują?".
- **Kontekstowa Pamięć:** Historia rozmów i inteligentne podpowiedzi.

### 🛒 Smart Shopping & Zero Waste
- **Dynamiczne Listy Zakupów:** Generowanie list na podstawie zaplanowanych posiłków i brakujących składników.
- **Warianty Sklepowe:** System rozpoznaje, że "Lidl Mleko" i "Biedronka Mleko" to ten sam produkt, pozwalając na porównywanie cen między marketami.
- **Alerty Ważności:** Powiadomienia o kończącej się dacie ważności produktów.

### 📊 Analityka i Zdrowie
- **Dashboard Finansowy:** Wykresy wydatków (dzienne, miesięczne), trendy zakupowe i podział na kategorie.
- **Analiza Żywieniowa:** Śledzenie wartości odżywczych kupowanych produktów (kalorie, makroskładniki) – *funkcja w wersji beta*.

### ⚡ Wydajność i Technologia
- **Full-Stack Architektura:** Nowoczesny frontend React 19 + wydajny backend FastAPI.
- **Optymlizacja:** Wirtualne przewijanie dla dużych list (tysiące pozycji), lazy loading dialogów, cache bazy danych i odpowiedzi LLM.

---

## 🚀 Szybki Start (Quick Start)

### Wymagania Wstępne
- **Python 3.10+**
- **Node.js 18+**
- **Ollama** z modelem `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` (lub innym)
- **Tesseract OCR** (zainstalowany w systemie)

### Instalacja (5 minut)

```bash
# Sklonuj repozytorium
git clone <repo-url>
cd ParagonOCR

# Windows (PowerShell) - Automatyczna konfiguracja
.\scripts\setup.ps1

# Uruchomienie serwerów deweloperskich (Backend + Frontend)
.\scripts\dev.ps1
```

**Dostęp:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Dokumentacja API: http://localhost:8000/docs

---

## 🏗️ Architektura Systemu

```mermaid
graph TD
    User[Użytkownik] --> Front[Frontend (React 19)]
    Front --> API[Backend API (FastAPI)]
    
    subgraph Data Layer
        API --> DB[(SQLite)]
        API --> Cache[LRU Cache]
    end
    
    subgraph AI Services
        API --> OCR[Tesseract OCR]
        API --> LLM[Ollama (Bielik LLM)]
        LLM --> RAG[RAG Engine]
    end
```

**Stos Technologiczny:**
- **Backend:** FastAPI, SQLAlchemy, Alembic, Pydantic
- **Frontend:** React, TypeScript, Vite, TailwindCSS, Zustand, Recharts
- **AI/ML:** LangChain (konceptualnie), SentenceTransformers (RAG/Embeddings), Tesseract
- **Inne:** WebAuthn (Logowanie kluczami Passkeys)

---

## 📁 Struktura Projektu

```
ParagonOCR/
├── backend/              # Logika biznesowa, API, obsługa AI
├── frontend/             # Interfejs użytkownika, komponenty React
├── docs/                 # Dokumentacja techniczna i projektowa
├── data/                 # Dane lokalne
│   ├── samples/          # Przykładowe paragony
│   └── uploads/          # Przetwarzane pliki
├── scripts/              # Skrypty automatyzujące i weryfikacyjne
│   ├── verification/     # Skrypty testujące pipeline i modele
│   └── utils/            # Narzędzia pomocnicze
└── archive/              # Archiwum starszych wersji
```

---

## 📊 Status Projektu

**Wersja:** 1.0.0-beta
**Data aktualizacji:** 2025-12-28
**Status:** ✅ Aktywny Rozwój (Active Development)

**Ostatnio wdrożone:**
- ✅ Pełna obsługa RAG (Rozmowa z własnymi danymi).
- ✅ System Smart Shopping i redukcji marnowania żywności.
- ✅ Optymalizacja wydajności GUI i zapytań bazodanowych.
- ✅ Logowanie biometryczne (Passkeys/FIDO2).

---

## 🤝 Wsparcie i Kontakt

Jeśli masz pytania, sugestie lub znalazłeś błąd:
- **Issues:** Zgłoś problem na GitHubie.
- **Discussions:** Dołącz do dyskusji o rozwoju projektu.
- **Autor:** [CodeMarcinu](https://github.com/codemarcinu)

---

## 📝 Licencja

Projekt udostępniany na licencji MIT. Zobacz plik [LICENSE](LICENSE) po więcej szczegółów.
