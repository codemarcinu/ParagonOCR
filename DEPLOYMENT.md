# 🚀 ParagonWeb - Przewodnik Deployment

## Spis treści

1. [Deployment lokalny](#deployment-lokalny)
2. [Deployment Docker](#deployment-docker)
3. [Deployment na serwerze](#deployment-na-serwerze)
4. [Deployment w chmurze](#deployment-w-chmurze)
5. [Backup i restore](#backup-i-restore)
6. [Monitoring](#monitoring)
7. [Bezpieczeństwo](#bezpieczeństwo)

---

## Deployment lokalny

### Windows

**Krok 1:** Zainstaluj Python 3.13+
```powershell
# Pobierz z python.org lub użyj winget
winget install Python.Python.3.13
```

**Krok 2:** Utwórz środowisko wirtualne
```powershell
python -m venv venv
venv\Scripts\activate
```

**Krok 3:** Zainstaluj zależności
```powershell
cd ReceiptParser
pip install -r requirements.txt
```

**Krok 4:** Konfiguracja
```powershell
# Utwórz .env
@"
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
"@ | Out-File -FilePath .env -Encoding utf8
```

**Krok 5:** Inicjalizuj bazę
```powershell
python -m ReceiptParser.src.main init-db
```

**Krok 6:** Uruchom
```powershell
# Terminal 1
python server.py

# Terminal 2
python web_app.py
```

### Linux/Mac

**Krok 1:** Zainstaluj Python 3.13+
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.13 python3.13-venv

# Mac (Homebrew)
brew install python@3.13
```

**Krok 2:** Utwórz środowisko wirtualne
```bash
python3.13 -m venv venv
source venv/bin/activate
```

**Krok 3:** Zainstaluj zależności
```bash
cd ReceiptParser
pip install -r requirements.txt
```

**Krok 4:** Konfiguracja
```bash
cat > .env << EOF
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
EOF
```

**Krok 5:** Inicjalizuj bazę
```bash
python -m ReceiptParser.src.main init-db
```

**Krok 6:** Uruchom jako service (opcjonalnie)

Utwórz plik `/etc/systemd/system/paragonweb.service`:
```ini
[Unit]
Description=ParagonWeb Application
After=network.target

[Service]
Type=simple
User=twoj-user
WorkingDirectory=/path/to/ParagonOCR
Environment="PATH=/path/to/ParagonOCR/venv/bin"
ExecStart=/path/to/ParagonOCR/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Aktywuj service:
```bash
sudo systemctl enable paragonweb
sudo systemctl start paragonweb
```

---

## Deployment Docker

### Podstawowy deployment

**Krok 1:** Sklonuj repozytorium
```bash
git clone <repo-url>
cd ParagonOCR
git checkout feature/web-app-transformation
```

**Krok 2:** Utwórz `.env`
```bash
cd ReceiptParser
cat > .env << EOF
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
EOF
```

**Krok 3:** Zbuduj i uruchom
```bash
cd ..
docker-compose up -d --build
```

**Krok 4:** Sprawdź logi
```bash
docker-compose logs -f
```

### Production deployment

**1. Użyj docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  paragon-web:
    build: .
    container_name: paragon_ocr_prod
    restart: always
    ports:
      - "8000:8000"
      - "8080:8080"
    volumes:
      - ./ReceiptParser/data:/app/ReceiptParser/data
      - ./logs:/app/logs
      - ./paragony:/app/paragony
      - ./uploads:/app/uploads
    environment:
      - ENABLE_FILE_LOGGING=true
      - USE_CLOUD_AI=true
      - USE_CLOUD_OCR=true
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**2. Uruchom:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Reverse Proxy (Nginx)

**Konfiguracja Nginx:**

```nginx
server {
    listen 80;
    server_name paragonweb.example.com;

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (dla NiceGUI)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**SSL z Let's Encrypt:**
```bash
sudo certbot --nginx -d paragonweb.example.com
```

---

## Deployment na serwerze

### VPS (Ubuntu/Debian)

**Krok 1:** Przygotuj serwer
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git
sudo systemctl enable docker
sudo systemctl start docker
```

**Krok 2:** Sklonuj aplikację
```bash
cd /opt
sudo git clone <repo-url> paragonweb
cd paragonweb
git checkout feature/web-app-transformation
```

**Krok 3:** Konfiguracja
```bash
cd ReceiptParser
sudo nano .env
# Wprowadź klucze API
```

**Krok 4:** Uruchom
```bash
cd /opt/paragonweb
sudo docker-compose up -d
```

**Krok 5:** Firewall
```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Raspberry Pi

**Uwaga:** Raspberry Pi może być zbyt wolne dla trybu lokalnego (Ollama). Użyj trybu Cloud.

**Krok 1:** Zainstaluj Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Krok 2:** Sklonuj i uruchom (jak wyżej)

**Krok 3:** Monitoruj zasoby
```bash
htop
docker stats
```

---

## Deployment w chmurze

### AWS EC2

**Krok 1:** Utwórz instancję EC2 (Ubuntu 22.04)

**Krok 2:** Połącz się przez SSH
```bash
ssh -i key.pem ubuntu@ec2-xxx.amazonaws.com
```

**Krok 3:** Zainstaluj Docker
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
```

**Krok 4:** Sklonuj i uruchom aplikację (jak wyżej)

**Krok 5:** Security Group
- Otwórz porty 80, 443, 8000, 8080
- Ogranicz dostęp do 8000, 8080 tylko z Twojego IP

### Google Cloud Platform

**Krok 1:** Utwórz VM instance
```bash
gcloud compute instances create paragonweb \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud \
  --machine-type e2-medium \
  --boot-disk-size 20GB
```

**Krok 2:** Połącz się
```bash
gcloud compute ssh paragonweb
```

**Krok 3:** Zainstaluj i uruchom (jak wyżej)

### DigitalOcean

**Krok 1:** Utwórz Droplet (Ubuntu 22.04)

**Krok 2:** Połącz się przez SSH

**Krok 3:** Zainstaluj i uruchom (jak wyżej)

---

## Backup i restore

### Backup

**Automatyczny backup (cron):**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/paragonweb"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/paragonweb"

mkdir -p $BACKUP_DIR

# Backup bazy danych
cp $APP_DIR/ReceiptParser/data/receipts.db $BACKUP_DIR/receipts_$DATE.db

# Backup całego katalogu danych
tar -czf $BACKUP_DIR/data_$DATE.tar.gz $APP_DIR/ReceiptParser/data/

# Usuń backupi starsze niż 30 dni
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

**Dodaj do crontab:**
```bash
crontab -e
# Backup codziennie o 2:00
0 2 * * * /path/to/backup.sh
```

### Restore

**Przywróć bazę danych:**
```bash
# Zatrzymaj aplikację
docker-compose down

# Przywróć bazę
cp /backups/paragonweb/receipts_20250115_020000.db \
   ReceiptParser/data/receipts.db

# Uruchom ponownie
docker-compose up -d
```

**Przywróć cały katalog danych:**
```bash
docker-compose down
tar -xzf /backups/paragonweb/data_20250115_020000.tar.gz -C .
docker-compose up -d
```

---

## Monitoring

### Health checks

**Backend:**
```bash
curl http://localhost:8000/
```

**Frontend:**
```bash
curl http://localhost:8080/
```

### Logi

**Docker:**
```bash
docker-compose logs -f
docker-compose logs -f --tail=100
```

**Lokalnie:**
```bash
tail -f logs/paragonocr_*.log
```

### Monitoring zasobów

**Docker stats:**
```bash
docker stats paragon_ocr
```

**System:**
```bash
htop
df -h
free -h
```

### Alerty (Przyszłość)

Można dodać:
- Prometheus + Grafana
- Sentry dla błędów
- Email/SMS notyfikacje

---

## Bezpieczeństwo

### Best practices

1. **Zmienne środowiskowe:**
   - Nigdy nie commituj `.env` do git
   - Używaj secret management (HashiCorp Vault, AWS Secrets Manager)

2. **Firewall:**
   ```bash
   # Ogranicz dostęp do API tylko z lokalnej sieci
   sudo ufw allow from 192.168.1.0/24 to any port 8000
   sudo ufw allow from 192.168.1.0/24 to any port 8080
   ```

3. **HTTPS:**
   - Zawsze używaj HTTPS w produkcji
   - Użyj Let's Encrypt (darmowe certyfikaty)

4. **Backup:**
   - Regularne backup bazy danych
   - Przechowuj backupi w bezpiecznym miejscu

5. **Updates:**
   ```bash
   # Regularnie aktualizuj zależności
   pip install --upgrade -r requirements.txt
   docker-compose pull
   docker-compose up -d --build
   ```

### Security headers (Nginx)

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

---

## Troubleshooting deployment

### Problem: Port już zajęty

**Rozwiązanie:**
```bash
# Znajdź proces
sudo lsof -i :8000
sudo lsof -i :8080

# Zabij proces
sudo kill -9 <PID>

# Lub zmień porty w docker-compose.yml
```

### Problem: Brak miejsca na dysku

**Rozwiązanie:**
```bash
# Wyczyść Docker
docker system prune -a

# Wyczyść stare logi
find logs/ -name "*.log" -mtime +30 -delete
```

### Problem: Aplikacja nie startuje

**Rozwiązanie:**
```bash
# Sprawdź logi
docker-compose logs

# Sprawdź konfigurację
docker-compose config

# Uruchom w trybie debug
docker-compose up (bez -d)
```

---

**Ostatnia aktualizacja:** 2025-01-XX

