# Junior Counsel Deployment Guide

## Overview

This guide covers deploying Junior Counsel to production. The system consists of:
- **Backend**: Python/Flask API with PostgreSQL + pgvector + Redis
- **Frontend**: Next.js 14 application (deployed to Vercel)
- **Workers**: Background job processors (RQ workers)

---

## Prerequisites

### System Requirements
- **Server**: Ubuntu 22.04 LTS (minimum 4GB RAM, 2 CPU cores)
- **Database**: PostgreSQL 16 with pgvector extension
- **Queue**: Redis 7+
- **Domain**: Valid domain name with SSL certificate
- **Docker**: Docker 24+ and Docker Compose 2+

### External Services
- **OpenAI API Key**: For embeddings and LLM (required)
- **Email Service** (optional): Resend API for notifications
- **Object Storage** (optional): AWS S3 or compatible for document storage

---

## Production Setup

### 1. Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx (for reverse proxy)
sudo apt-get install nginx certbot python3-certbot-nginx -y
```

### 2. Clone Repository

```bash
# Create app directory
sudo mkdir -p /opt/junior-counsel
sudo chown $USER:$USER /opt/junior-counsel

# Clone repository
cd /opt/junior-counsel
git clone https://github.com/willieprinsloo/JuniorCounsel.git .
```

### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables**:

```bash
# Database
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD@postgres:5432/junior_counsel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE
POSTGRES_DB=junior_counsel

# Redis
REDIS_URL=redis://redis:6379/0

# Application
ENV=production
SECRET_KEY=GENERATE_STRONG_SECRET_KEY_HERE
DEBUG=False

# API Keys
OPENAI_API_KEY=sk-...

# Optional: Email
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@yourdomain.com

# Optional: AWS (for S3 storage)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=af-south-1
S3_BUCKET=junior-counsel-uploads
```

**Generate Secure Secret Key**:
```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

### 4. Build and Start Services

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Run Database Migrations

```bash
# Run migrations
docker-compose exec backend python database/migrate.py

# Verify database
docker-compose exec postgres psql -U postgres -d junior_counsel -c "\dt"
```

### 6. Create Admin User

```bash
# Connect to backend container
docker-compose exec backend python

# In Python shell:
from src.app.core.db import session_scope
from src.app.persistence.models import User, Organisation, OrganisationUser
from src.app.core.security import hash_password

with session_scope() as db:
    # Create organisation
    org = Organisation(
        name="Your Law Firm",
        contact_email="admin@yourfirm.co.za",
        is_active=True
    )
    db.add(org)
    db.flush()

    # Create admin user
    admin = User(
        email="admin@yourfirm.co.za",
        password_hash=hash_password("CHANGE_THIS_PASSWORD"),
        full_name="Admin User",
        is_active=True
    )
    db.add(admin)
    db.flush()

    # Link user to organisation
    org_user = OrganisationUser(
        organisation_id=org.id,
        user_id=admin.id,
        role="admin"
    )
    db.add(org_user)
    db.commit()

exit()
```

### 7. Configure Nginx Reverse Proxy

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/junior-counsel
```

**Nginx Configuration**:

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 50M;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/junior-counsel /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 8. Configure SSL with Let's Encrypt

```bash
# Obtain SSL certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal (already configured by certbot)
sudo certbot renew --dry-run
```

---

## Frontend Deployment (Vercel)

### 1. Push Frontend to GitHub

```bash
# Ensure frontend code is pushed
git add frontend/
git commit -m "Frontend ready for deployment"
git push origin main
```

### 2. Deploy to Vercel

1. Go to https://vercel.com
2. Import your GitHub repository
3. Configure build settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

4. Set Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://api.yourdomain.com
   NEXT_PUBLIC_APP_NAME=Junior Counsel
   ```

5. Deploy!

---

## CI/CD Setup (GitHub Actions)

### 1. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets → Actions:

```
# Docker Hub
DOCKER_USERNAME=your-username
DOCKER_PASSWORD=your-password

# Deployment Server
DEPLOY_HOST=your-server-ip
DEPLOY_USER=ubuntu
DEPLOY_SSH_KEY=<your-private-ssh-key>

# Vercel (Frontend)
VERCEL_TOKEN=<vercel-token>
VERCEL_ORG_ID=<org-id>
VERCEL_PROJECT_ID=<project-id>
PRODUCTION_API_URL=https://api.yourdomain.com
```

### 2. Trigger Deployment

```bash
# Create a release tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

This will trigger the deployment workflow automatically.

---

## Monitoring and Maintenance

### Health Checks

```bash
# Backend health
curl https://api.yourdomain.com/health

# Database connection
docker-compose exec postgres pg_isready

# Redis connection
docker-compose exec redis redis-cli ping
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Backup Database

```bash
# Create backup
docker-compose exec postgres pg_dump -U postgres junior_counsel > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose exec -T postgres psql -U postgres junior_counsel < backup_20260312_120000.sql
```

### Update Application

```bash
# Pull latest code
cd /opt/junior-counsel
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d

# Run any new migrations
docker-compose exec backend python database/migrate.py
```

### Scale Workers

```bash
# Scale to 3 worker instances
docker-compose up -d --scale worker=3

# View worker status
docker-compose ps worker
```

---

## Performance Tuning

### PostgreSQL Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM documents WHERE case_id = '...';

-- Update statistics
ANALYZE documents;

-- Reindex if needed
REINDEX TABLE documents;
```

### Redis Memory Limit

```bash
# Edit docker-compose.yml
services:
  redis:
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Gunicorn Workers

```bash
# Edit Dockerfile CMD
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "src.app.main:app"]
```

---

## Security Checklist

- [ ] Strong passwords for all services
- [ ] SSL/TLS enabled (Let's Encrypt)
- [ ] Firewall configured (UFW)
- [ ] Database not exposed to public internet
- [ ] Environment variables secured (.env not in git)
- [ ] Regular security updates (apt-get upgrade)
- [ ] Backup strategy in place
- [ ] CORS configured correctly
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] File upload restrictions enforced

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database connection failed → Check DATABASE_URL
# 2. Secret key missing → Set SECRET_KEY in .env
# 3. OpenAI API key invalid → Verify OPENAI_API_KEY
```

### Workers not processing jobs

```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec backend python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Restart workers
docker-compose restart worker
```

### Database migrations fail

```bash
# Check migration status
docker-compose exec backend python database/migrate.py --status

# Reset database (CAUTION: Deletes all data!)
docker-compose exec backend python database/migrate.py --reset
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean logs
sudo journalctl --vacuum-time=7d
```

---

## Support

For issues and questions:
- **GitHub Issues**: https://github.com/willieprinsloo/JuniorCounsel/issues
- **Documentation**: `/documentation` directory
- **Email**: support@yourdomain.com

---

**Last Updated**: 2026-03-12
**Version**: 1.0.0
