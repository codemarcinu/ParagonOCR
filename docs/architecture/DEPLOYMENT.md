# 🚀 Deployment Guide

Complete guide for deploying ParagonOCR Web Edition to production.

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Best for:** Single server deployments, development/staging environments

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Steps:**

1. **Clone repository:**
   ```bash
   git clone <repo-url>
   cd ParagonOCR
   ```

2. **Configure environment:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with production values
   ```

3. **Build and start:**
   ```bash
   docker-compose up -d --build
   ```

4. **Run migrations:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Verify:**
   - Backend: http://localhost:8000/health
   - Frontend: http://localhost:5173

**Docker Compose Configuration:**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/receipts.db
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./backend/data:/app/data
      - ./data/uploads:/app/uploads

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
```

### Option 2: Manual Deployment

**Best for:** Custom server configurations, cloud platforms

#### Backend Deployment

**Requirements:**
- Python 3.10+
- System dependencies (Tesseract, Poppler)
- Ollama running separately

**Steps:**

1. **Setup server:**
   ```bash
   # Install system dependencies
   sudo apt-get update
   sudo apt-get install python3.10 python3.10-venv tesseract-ocr poppler-utils nginx
   ```

2. **Clone and setup:**
   ```bash
   git clone <repo-url>
   cd ParagonOCR/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure:**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start with Gunicorn:**
   ```bash
   gunicorn app.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --timeout 120
   ```

6. **Setup systemd service:**
   ```ini
   # /etc/systemd/system/paragonocr-backend.service
   [Unit]
   Description=ParagonOCR Backend
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/opt/paragonocr/backend
   Environment="PATH=/opt/paragonocr/backend/venv/bin"
   ExecStart=/opt/paragonocr/backend/venv/bin/gunicorn \
     app.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 127.0.0.1:8000

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable paragonocr-backend
   sudo systemctl start paragonocr-backend
   ```

#### Frontend Deployment

**Build for production:**
```bash
cd frontend
npm install
npm run build
```

**Serve with Nginx:**
```nginx
# /etc/nginx/sites-available/paragonocr
server {
    listen 80;
    server_name your-domain.com;

    root /opt/paragonocr/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/paragonocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 3: Cloud Platforms

#### Heroku

**Backend:**
```bash
# Create Procfile
echo "web: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker" > Procfile

# Deploy
heroku create paragonocr-backend
git push heroku main
```

**Frontend:**
- Use Vercel, Netlify, or similar
- Set `VITE_API_URL` environment variable

#### AWS (EC2 + S3)

1. **Launch EC2 instance**
2. **Install dependencies**
3. **Setup Nginx reverse proxy**
4. **Use S3 for file storage**
5. **Configure RDS for database** (optional, upgrade from SQLite)

#### DigitalOcean App Platform

1. **Connect GitHub repository**
2. **Configure build settings:**
   - Backend: Python buildpack
   - Frontend: Node.js buildpack
3. **Set environment variables**
4. **Deploy**

## Production Configuration

### Environment Variables

**Backend (.env):**
```ini
# Database
DATABASE_URL=sqlite:///./data/receipts.db
# Or PostgreSQL: postgresql://user:pass@localhost/dbname

# Security
SECRET_KEY=<generate-strong-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=https://your-domain.com

# File Upload
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.pdf,.png,.jpg,.jpeg,.tiff

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
```

**Frontend (.env.production):**
```ini
VITE_API_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com
```

### Security Checklist

- [ ] **Strong SECRET_KEY** - Generate with `openssl rand -hex 32`
- [ ] **HTTPS enabled** - Use Let's Encrypt SSL certificates
- [ ] **CORS configured** - Only allow your domain
- [ ] **Rate limiting** - Configured on auth endpoints
- [ ] **File upload limits** - Max size enforced
- [ ] **Database backups** - Automated backup schedule
- [ ] **Environment variables** - Not committed to git
- [ ] **Firewall rules** - Only necessary ports open

### Performance Optimization

**Backend:**
- Use **Gunicorn** with multiple workers
- Enable **GZip compression**
- Use **connection pooling** for database
- Consider **Redis** for caching (future)

**Frontend:**
- **Code splitting** enabled
- **Asset optimization** (minification, compression)
- **CDN** for static assets (optional)
- **Service worker** for offline support (future)

**Database:**
- **PostgreSQL** for production (upgrade from SQLite)
- **Connection pooling** configured
- **Indexes** optimized
- **Regular VACUUM** (if SQLite)

### Monitoring

**Application Monitoring:**
- **Logging** - Structured logs to file/Syslog
- **Error tracking** - Sentry or similar
- **Performance monitoring** - APM tools
- **Health checks** - `/health` endpoint

**System Monitoring:**
- **Server resources** - CPU, memory, disk
- **Database size** - Monitor growth
- **Ollama status** - Ensure service running
- **Backup verification** - Test restore process

### Backup Strategy

**Database Backups:**
```bash
# SQLite backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/paragonocr"
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/paragonocr/backend/data/receipts.db \
   "$BACKUP_DIR/receipts_$DATE.db"

# Keep last 30 days
find "$BACKUP_DIR" -name "receipts_*.db" -mtime +30 -delete
```

**File Backups:**
- Backup `data/uploads/` directory
- Use cloud storage (S3, Backblaze) for redundancy

**Automated Backups:**
```bash
# Add to crontab
0 2 * * * /opt/paragonocr/scripts/backup.sh
```

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check logs: `journalctl -u paragonocr-backend`
- Verify database permissions
- Check Ollama connection

**Frontend build fails:**
- Clear cache: `rm -rf node_modules .vite`
- Check environment variables
- Verify API URL is correct

**Database locked:**
- Check for long-running transactions
- Restart backend service
- Consider PostgreSQL for production

**Ollama connection errors:**
- Verify Ollama is running
- Check firewall rules
- Verify model is downloaded

## Scaling

### Horizontal Scaling

- **Load balancer** (Nginx, HAProxy)
- **Multiple backend instances**
- **Shared database** (PostgreSQL)
- **Shared file storage** (S3, NFS)

### Vertical Scaling

- **More CPU/RAM** for Ollama
- **Faster storage** for database
- **SSD** for file storage

## Maintenance

### Regular Tasks

- **Database backups** - Daily
- **Log rotation** - Weekly
- **Security updates** - Monthly
- **Dependency updates** - Quarterly

### Update Procedure

1. **Backup database and files**
2. **Pull latest code**
3. **Run migrations:** `alembic upgrade head`
4. **Restart services**
5. **Verify health checks**

---

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

