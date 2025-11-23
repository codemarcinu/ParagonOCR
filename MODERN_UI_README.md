# 🍽️ Spiżarnia AI - Nowoczesny Interfejs

Nowoczesny, mobile-first interfejs użytkownika dla ParagonWeb, zaprojektowany z myślą o użytkownikach nietechnicznych.

**Data aktualizacji:** 2025-11-23

## ✨ Główne Zmiany

### Design System "KitchenOS"
- **Paleta kolorów**: Szałwiowa zieleń (`emerald-600`), ciepły beż (`slate-50`), terracotta (`orange-100`) dla ostrzeżeń
- **Mobile-First**: Duże przyciski, bottom navigation na telefonie, responsive layout
- **Karty zamiast tabel**: Wizualne reprezentacje zamiast suchych danych

### Nowe Funkcje

1. **Dashboard - Centrum Dowodzenia**
   - Karty szybkiego statusu (Do zużycia, Magazyn, Lista, Co zjeść?)
   - Wielkie pole uploadu z animacjami hover
   - Ostatnie paragony jako karty z możliwością kliknięcia
   - Floating Action Button (FAB) w prawym dolnym rogu

2. **Wizard Uploadu Paragonów**
   - Animowane kroki przetwarzania:
     - 📤 Przesyłanie pliku
     - 🔍 Analizuję obraz...
     - 🤖 Asystent czyta produkty...
     - 📦 Układam na półkach...
   - Pasek postępu z "ludzkimi" komunikatami
   - Opcjonalne logi techniczne (collapsible)

3. **Wirtualna Lodówka**
   - Grid z kartami produktów
   - Paski świeżości (zielony → żółty → pomarańczowy → czerwony)
   - Filtry kategorii jako "chipsy" (zaokrąglone przyciski)
   - Emoji dla kategorii (🥛 Nabiał, 🥦 Warzywa, etc.)
   - Relatywne daty (Dzisiaj!, Jutro!, Za X dni)

4. **Nowoczesny Chat z Asystentem AI**
   - Dymki jak w Messengerze/WhatsApp
   - Wiadomości użytkownika po prawej (zielone)
   - Odpowiedzi asystenta po lewej (jasnozielone)
   - Animacja "Asystent myśli..." podczas przetwarzania

5. **Bottom Navigation (Mobile)**
   - Stały pasek nawigacji na dole ekranu
   - FAB na środku (większy, z cieniem)
   - Ukryty na desktopie (min-width: 768px)

## 🚀 Uruchomienie

### Opcja 1: Bezpośrednio (zamiast web_app.py)

```bash
python modern_ui.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8082`

### Opcja 2: Przez zmienną środowiskową

Możesz zmienić port w kodzie lub dodać zmienną środowiskową:

```bash
PORT=8082 python modern_ui.py
```

## 📱 Responsywność

- **Mobile (< 768px)**: Bottom navigation, większe przyciski, pojedyncza kolumna
- **Tablet (768px - 1024px)**: 2-3 kolumny w gridach
- **Desktop (> 1024px)**: 4 kolumny, ukryty bottom nav, więcej przestrzeni

## 🎨 Komponenty

### Theme Class
Wszystkie kolory są zdefiniowane w klasie `Theme`:
- `PRIMARY`: `bg-emerald-600` (główny kolor)
- `SURFACE`: `bg-white shadow-sm rounded-xl` (karty)
- `ACCENT_WARN`: `bg-orange-100 text-orange-700` (ostrzeżenia)
- `CATEGORY_COLORS`: Mapowanie kategorii na kolory

### Funkcje pomocnicze
- `get_category_emoji()`: Zwraca emoji dla kategorii
- `get_freshness_color()`: Kolor paska świeżości na podstawie daty
- `format_date_relative()`: Formatuje datę relatywnie (Dzisiaj!, Jutro!, etc.)

## 🔄 Migracja z web_app.py

Nowy interfejs jest w pełni kompatybilny z istniejącym API (`server.py`). Wszystkie endpointy działają tak samo:

- `POST /api/upload` - Upload paragonu
- `GET /api/task/{task_id}` - Status zadania
- `GET /api/receipts` - Lista paragonów
- `GET /api/inventory` - Stan magazynu
- `POST /api/chat` - Chat z asystentem AI
- `POST /api/inventory/confirm` - Potwierdzenie produktów

## 🐛 Znane Problemy / TODO

1. **Lista zakupów**: Obecnie placeholder - wymaga implementacji logiki generowania list
2. **FAB trigger**: Używa JavaScript do kliknięcia na ukrytym input - może wymagać poprawy w niektórych przeglądarkach
3. **Dark mode**: Nie zaimplementowany (można dodać później)

## 📝 Uwagi Techniczne

- Wszystkie style używają Tailwind CSS (wbudowany w NiceGUI)
- Animacje CSS dla płynnych przejść
- Custom scrollbar dla lepszego UX
- Responsive grid z `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`

## 🎯 Następne Kroki

1. Dodać listę zakupów z generowaniem przez asystenta AI
2. Dodać tryb "W sklepie" (skreślanie produktów)
3. Dodać sugestie asystenta na dashboardzie
4. Dodać dark mode toggle
5. Dodać ikony SVG dla kategorii (zamiast emoji)

---

**Autor**: Implementacja zgodnie z wizją "Spiżarnia AI" - transformacja ParagonWeb w nowoczesnego asystenta domowego.

