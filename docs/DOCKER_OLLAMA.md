# 🐳 ParagonWeb + Ollama w Dockerze

## Przegląd

ParagonWeb może działać w dwóch trybach:
1. **Cloud** (domyślny) - OpenAI + Mistral OCR
2. **Lokalny** - Ollama + Tesseract

W trybie lokalnym, ParagonWeb może używać Ollama na kilka sposobów:
- **Istniejący kontener Ollama** (zalecane) - jeśli masz już uruchomiony Ollama
- **Nowy kontener Ollama** - jeśli potrzebujesz osobnego kontenera dla tego projektu
- **Ollama na hoście** - jeśli Ollama działa bezpośrednio na systemie (poza Dockerem)

## ⚠️ Ważne: Nie twórz drugiego kontenera Ollama!

Jeśli masz już uruchomiony kontener Ollama (np. systemowy), **NIE TWÓRZ DRUGIEGO**! 
Użyj istniejącego, ustawiając odpowiedni `OLLAMA_HOST` w docker-compose.yml.

## Architektura Docker

### Opcja 1: Istniejący kontener Ollama (zalecane)
```
┌─────────────────────────────────────────┐
│         Docker Network                  │
│                                         │
│  ┌──────────────┐                      │
│  │  ParagonWeb  │───▶ (istniejący)     │
│  │  Container   │    Ollama Container  │
│  │  :8000, :8080│    :11434            │
│  └──────────────┘                      │
│                                         │
└─────────────────────────────────────────┘
```

### Opcja 2: Nowy kontener Ollama (tylko jeśli potrzebny)
```
┌─────────────────────────────────────────┐
│         Docker Network                  │
│                                         │
│  ┌──────────────┐    ┌──────────────┐ │
│  │  ParagonWeb  │───▶│   Ollama     │ │
│  │  Container   │    │  Container   │ │
│  │  :8000, :8080│    │   :11434     │ │
│  └──────────────┘    └──────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

### Opcja 3: Ollama na hoście
```
┌─────────────────────────────────────────┐
│         Docker Network                  │
│                                         │
│  ┌──────────────┐                      │
│  │  ParagonWeb  │───▶ host.docker.     │
│  │  Container   │    internal:11434    │
│  │  :8000, :8080│    (Ollama na hoście)│
│  └──────────────┘                      │
│                                         │
└─────────────────────────────────────────┘
```

## Konfiguracja

### Użycie istniejącego kontenera Ollama

Jeśli masz już uruchomiony kontener Ollama, znajdź jego nazwę lub IP:

```bash
# Sprawdź uruchomione kontenery Ollama
docker ps | grep ollama

# Sprawdź IP kontenera
docker inspect <nazwa_kontenera> | grep IPAddress
```

Następnie w `docker-compose.yml` ustaw:

```yaml
services:
  paragon-web:
    environment:
      # Jeśli kontener jest w tej samej sieci Docker:
      - OLLAMA_HOST=http://<nazwa_kontenera>:11434
      # Lub użyj IP kontenera:
      - OLLAMA_HOST=http://<IP_kontenera>:11434
```

**WAŻNE:** Upewnij się, że oba kontenery są w tej samej sieci Docker:
```bash
# Sprawdź sieć istniejącego kontenera
docker inspect <nazwa_kontenera> | grep NetworkMode

# Jeśli są w różnych sieciach, połącz je:
docker network connect <nazwa_sieci> <nazwa_kontenera_ollama>
```

### Użycie Ollama na hoście (poza Dockerem)

Jeśli Ollama działa bezpośrednio na systemie:

```yaml
# docker-compose.yml
services:
  paragon-web:
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434  # Windows/Mac
      # lub dla Linuxa (sprawdź IP mostu docker0):
      - OLLAMA_HOST=http://172.17.0.1:11434  # Linux (docker0 bridge)
```

Aby znaleźć IP mostu docker0 na Linuxie:
```bash
ip addr show docker0 | grep inet
```

### Utworzenie nowego kontenera Ollama (tylko jeśli potrzebny)

Jeśli naprawdę potrzebujesz nowego kontenera, odkomentuj serwis `ollama` w `docker-compose.yml`:
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: paragon_ollama
    # ... reszta konfiguracji
```

## Sprawdzanie istniejącego Ollama

**PRZED uruchomieniem ParagonWeb, sprawdź czy masz już Ollama:**

```bash
# Sprawdź kontenery Docker z Ollama
docker ps -a | grep ollama

# Sprawdź czy Ollama działa na hoście (port 11434)
curl http://localhost:11434/api/tags

# Sprawdź wszystkie kontenery Ollama (również zatrzymane)
docker ps -a --filter "ancestor=ollama/ollama"
```

Jeśli masz już Ollama:
1. **Kontener Docker:** Ustaw `OLLAMA_HOST` na nazwę kontenera lub jego IP (patrz sekcja "Konfiguracja" wyżej)
2. **Na hoście:** Ustaw `OLLAMA_HOST` na `http://host.docker.internal:11434` (Mac/Windows) lub `http://172.17.0.1:11434` (Linux)
3. **NIE TWÓRZ** nowego kontenera Ollama w docker-compose.yml!

## Uruchomienie

### Tryb Cloud (domyślny)

```bash
docker-compose up -d
```

W trybie Cloud, Ollama nie jest używane (nawet jeśli jest uruchomione).

### Tryb Lokalny

**Jeśli masz już Ollama:**
1. Ustaw `OLLAMA_HOST` w `docker-compose.local.yml` (patrz sekcję "Konfiguracja")
2. Zakomentuj serwis `ollama` w `docker-compose.local.yml` (lub usuń `depends_on`)
3. Uruchom:
```bash
docker-compose -f docker-compose.local.yml up -d
```

**Jeśli potrzebujesz nowego kontenera Ollama:**
```bash
# Użyj specjalnego docker-compose dla trybu lokalnego
docker-compose -f docker-compose.local.yml up -d
```

## Pobieranie modeli Ollama

### Automatyczne

Modele są pobierane automatycznie przy pierwszym użyciu. To może zająć kilka minut.

### Ręczne

```bash
# Połącz się z kontenerem Ollama
docker exec -it paragon_ollama ollama pull llava:latest
docker exec -it paragon_ollama ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M

# Sprawdź pobrane modele
docker exec -it paragon_ollama ollama list
```

## Sprawdzanie statusu

### Czy Ollama działa?

```bash
# Sprawdź kontener
docker ps | grep ollama

# Sprawdź logi
docker logs paragon_ollama

# Sprawdź API
docker exec paragon_ollama curl http://localhost:11434/api/tags
```

### Czy ParagonWeb łączy się z Ollama?

```bash
# Sprawdź logi ParagonWeb
docker logs paragon_ocr | grep -i ollama

# Sprawdź konfigurację
docker exec paragon_ocr env | grep OLLAMA
```

## Troubleshooting

### Problem: "Nie można połączyć się z Ollama"

**Rozwiązanie:**
1. Sprawdź czy kontener Ollama działa:
   ```bash
   docker ps | grep ollama
   ```

2. Sprawdź czy są w tej samej sieci:
   ```bash
   docker network inspect paragonocr_default
   ```

3. Sprawdź OLLAMA_HOST w ParagonWeb:
   ```bash
   docker exec paragon_ocr env | grep OLLAMA_HOST
   # Powinno być: OLLAMA_HOST=http://ollama:11434
   ```

### Problem: "Model nie znaleziony"

**Rozwiązanie:**
```bash
# Pobierz model ręcznie
docker exec -it paragon_ollama ollama pull llava:latest

# Sprawdź dostępne modele
docker exec -it paragon_ollama ollama list
```

### Problem: "Wolne przetwarzanie"

**Rozwiązanie:**
- Ollama w Dockerze może być wolne na słabszym sprzęcie
- Rozważ użycie trybu Cloud (OpenAI jest szybsze)
- Lub zwiększ zasoby dla kontenera Ollama:
  ```yaml
  ollama:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
  ```

## Przełączanie między trybami

### Z Cloud na Lokalny

1. Zatrzymaj kontenery:
   ```bash
   docker-compose down
   ```

2. Uruchom z konfiguracją lokalną:
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

3. Upewnij się, że modele są pobrane (patrz wyżej)

### Z Lokalnego na Cloud

1. Zatrzymaj kontenery:
   ```bash
   docker-compose -f docker-compose.local.yml down
   ```

2. Uruchom standardowy docker-compose:
   ```bash
   docker-compose up -d
   ```

## Volume dla modeli Ollama

Modele Ollama są przechowywane w volume `ollama_data`, więc są zachowywane między restartami:

```bash
# Sprawdź volume
docker volume ls | grep ollama

# Backup modeli (opcjonalnie)
docker run --rm -v ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz /data
```

## Wydajność

### Zalecenia

- **Cloud (OpenAI):** Najszybsze, najlepsze dla produkcji
- **Lokalny (Ollama):** Wymaga mocnego sprzętu (GPU zalecane)
- **Hybrydowy:** Cloud OCR + Lokalny AI (kompromis)

### Zasoby dla Ollama

Minimalne:
- 4GB RAM
- 2 CPU cores
- 10GB miejsca na dysku (dla modeli)

Zalecane:
- 8GB+ RAM
- 4+ CPU cores
- GPU (CUDA) dla szybszego przetwarzania
- 20GB+ miejsca na dysku

## Bezpieczeństwo

- Ollama w Dockerze jest izolowane od hosta
- Komunikacja między kontenerami odbywa się przez sieć Docker (nie jest eksponowana na zewnątrz)
- Port 11434 jest eksponowany tylko jeśli chcesz użyć Ollama z hosta

## Przydatne komendy

```bash
# Restart Ollama
docker restart paragon_ollama

# Wyczyść cache Ollama
docker exec paragon_ollama ollama rm <model_name>

# Sprawdź użycie zasobów
docker stats paragon_ollama

# Zobacz wszystkie modele
docker exec -it paragon_ollama ollama list

# Usuń wszystkie modele (ostrożnie!)
docker exec -it paragon_ollama ollama list | awk '{print $1}' | xargs -I {} docker exec paragon_ollama ollama rm {}
```

---

**Ostatnia aktualizacja:** 2025-11-23

