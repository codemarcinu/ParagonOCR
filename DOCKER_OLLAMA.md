# 🐳 ParagonWeb + Ollama w Dockerze

## Przegląd

ParagonWeb może działać w dwóch trybach:
1. **Cloud** (domyślny) - OpenAI + Mistral OCR
2. **Lokalny** - Ollama + Tesseract

W trybie lokalnym, Ollama działa w osobnym kontenerze Docker i komunikuje się z ParagonWeb przez sieć Docker.

## Architektura Docker

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

## Konfiguracja

### Automatyczna konfiguracja

W Dockerze, `OLLAMA_HOST` jest automatycznie ustawiane na `http://ollama:11434` (nazwa serwisu Docker).

**Nie musisz tego konfigurować ręcznie!**

### Ręczna konfiguracja (opcjonalnie)

Jeśli chcesz użyć zewnętrznego Ollama (poza Dockerem):

```yaml
# docker-compose.yml
services:
  paragon-web:
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434  # Windows/Mac
      # lub
      - OLLAMA_HOST=http://172.17.0.1:11434  # Linux (docker0 bridge)
```

## Uruchomienie

### Tryb Cloud (domyślny)

```bash
docker-compose up -d
```

Kontener Ollama jest uruchamiany, ale nie jest używany (chyba że przełączysz na tryb lokalny).

### Tryb Lokalny

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

