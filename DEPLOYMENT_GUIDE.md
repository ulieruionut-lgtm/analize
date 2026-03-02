# 🚀 Ghid Deployment Online - Aplicație Analize Medicale

Aplicația este pregătită pentru deployment online cu suport pentru:
- **SQLite** (local/testare)
- **PostgreSQL** (recomandat pentru producție)
- **MySQL** (compatibil PHP hosting)

---

## 📋 Opțiuni de Deployment

### 1. Railway.app (RECOMANDAT - GRATUIT)
✅ Gratuit pentru început (500h/lună)
✅ PostgreSQL inclus gratuit
✅ Deploy automat din GitHub
✅ HTTPS automat

### 2. Render.com (GRATUIT)
✅ Plan gratuit permanent
✅ PostgreSQL inclus
✅ HTTPS automat
⚠️ Se oprește după 15 min inactivitate

### 3. VPS Manual (DigitalOcean, Contabo, etc.)
✅ Control total
✅ Orice bază de date (MySQL, PostgreSQL)
⚠️ Necesită configurare manuală
💰 5-10€/lună

---

## 🎯 Opțiunea 1: Railway.app (CEL MAI SIMPLU)

### Pas 1: Pregătire cod

```bash
# Instalează dependințele noi
pip install -r requirements.txt
```

### Pas 2: Creează cont Railway

1. Mergi la [railway.app](https://railway.app)
2. Sign up cu GitHub
3. Click "New Project"

### Pas 3: Deploy aplicație

#### A. Din GitHub (RECOMANDAT)

1. **Push codul pe GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Pregătire deployment"
   git branch -M main
   git remote add origin https://github.com/USERNAME/analize-medicale.git
   git push -u origin main
   ```

2. **În Railway**:
   - Click "Deploy from GitHub repo"
   - Selectează repository-ul
   - Railway detectează automat Dockerfile

#### B. Din CLI (ALTERNATIV)

```bash
# Instalează Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway init
railway up
```

### Pas 4: Adaugă PostgreSQL

1. În Railway dashboard, click "+ New"
2. Selectează "Database" → "PostgreSQL"
3. Railway creează automat `DATABASE_URL`

### Pas 5: Rulează migrații

```bash
# Conectează-te la Railway
railway link

# Rulează migrații
railway run python run_migrations.py
```

### Pas 6: Configurare variabile mediu

În Railway dashboard → Variables:
```
DATABASE_URL = postgresql://... (generat automat)
OCR_LANG = ron
PDF_TEXT_MIN_CHARS = 200
```

### Pas 7: Accesare aplicație

Railway îți dă URL-ul: `https://your-app.railway.app`

---

## 🎯 Opțiunea 2: Render.com (GRATUIT PERMANENT)

### Pas 1: Creează cont Render

1. Mergi la [render.com](https://render.com)
2. Sign up cu GitHub

### Pas 2: Creează PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Nume: `analize-db`
3. Plan: Free
4. Creează și salvează `Internal Database URL`

### Pas 3: Creează Web Service

1. Click "New +" → "Web Service"
2. Connect Repository (GitHub)
3. Setări:
   - **Name**: analize-medicale
   - **Environment**: Docker
   - **Plan**: Free

### Pas 4: Variabile mediu

În "Environment":
```
DATABASE_URL = <Internal Database URL de la PostgreSQL>
OCR_LANG = ron
PDF_TEXT_MIN_CHARS = 200
PYTHON_VERSION = 3.11.0
```

### Pas 5: Deploy

Click "Create Web Service" - deploy automat!

### Pas 6: Rulează migrații

```bash
# În Render Shell (din dashboard)
python run_migrations.py
```

---

## 🎯 Opțiunea 3: VPS Manual (DigitalOcean, Contabo, etc.)

### Pas 1: Creează VPS

- **DigitalOcean**: Droplet Ubuntu 22.04 ($6/lună)
- **Contabo**: VPS S ($5/lună)
- **Hetzner**: CX11 (€4/lună)

### Pas 2: Conectare SSH

```bash
ssh root@YOUR_SERVER_IP
```

### Pas 3: Instalare dependințe

```bash
# Update sistem
apt update && apt upgrade -y

# Instalare Python 3.11
apt install -y python3.11 python3.11-venv python3-pip

# Instalare Tesseract OCR + limba română
apt install -y tesseract-ocr tesseract-ocr-ron

# Instalare Nginx
apt install -y nginx

# Instalare MySQL (opțional)
apt install -y mysql-server
mysql_secure_installation
```

### Pas 4: Configurare aplicație

```bash
# Creare user
adduser analize
su - analize

# Clone repo (sau upload via SFTP)
git clone https://github.com/USERNAME/analize-medicale.git
cd analize-medicale

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Instalare dependințe
pip install -r requirements.txt
```

### Pas 5: Configurare MySQL

```bash
# Conectare MySQL
mysql -u root -p

# Creare database
CREATE DATABASE analize CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'analize_user'@'localhost' IDENTIFIED BY 'PAROLA_SIGURA';
GRANT ALL PRIVILEGES ON analize.* TO 'analize_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Importare schema
mysql -u analize_user -p analize < sql/schema_mysql.sql
```

### Pas 6: Configurare .env

```bash
nano .env
```

Conținut:
```
DATABASE_URL=mysql://analize_user:PAROLA_SIGURA@localhost:3306/analize
OCR_LANG=ron
PDF_TEXT_MIN_CHARS=200
```

### Pas 7: Rulează migrații

```bash
python run_migrations.py
```

### Pas 8: Configurare systemd (pornire automată)

```bash
sudo nano /etc/systemd/system/analize.service
```

Conținut:
```ini
[Unit]
Description=Analize Medicale FastAPI
After=network.target

[Service]
Type=simple
User=analize
WorkingDirectory=/home/analize/analize-medicale
Environment="PATH=/home/analize/analize-medicale/venv/bin"
ExecStart=/home/analize/analize-medicale/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Activare serviciu
sudo systemctl daemon-reload
sudo systemctl enable analize
sudo systemctl start analize
sudo systemctl status analize
```

### Pas 9: Configurare Nginx (reverse proxy + HTTPS)

```bash
sudo nano /etc/nginx/sites-available/analize
```

Conținut:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activare site
sudo ln -s /etc/nginx/sites-available/analize /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Pas 10: Instalare SSL (Let's Encrypt)

```bash
# Instalare certbot
apt install -y certbot python3-certbot-nginx

# Obține certificat SSL
certbot --nginx -d your-domain.com

# Reneware automată
certbot renew --dry-run
```

---

## 📊 Comparație platforme

| Platformă | Cost | Setup | MySQL | PostgreSQL | HTTPS | Uptime |
|-----------|------|-------|-------|------------|-------|--------|
| **Railway** | Gratuit (500h) | ⭐⭐⭐⭐⭐ | ❌ | ✅ | ✅ | 100% |
| **Render** | Gratuit | ⭐⭐⭐⭐ | ❌ | ✅ | ✅ | Sleep after 15min |
| **VPS** | 5-10€/lună | ⭐⭐ | ✅ | ✅ | ✅ (manual) | 100% |

---

## 🔧 Configurare DATABASE_URL

### SQLite (local)
```
DATABASE_URL=sqlite
# sau gol
```

### PostgreSQL
```
DATABASE_URL=postgresql://user:password@host:5432/database
```

### MySQL
```
DATABASE_URL=mysql://user:password@host:3306/database
```

---

## 🧪 Testare după deployment

1. **Health check**:
   ```
   https://your-domain.com/health
   ```
   Răspuns: `{"status": "ok", "database": "connected"}`

2. **Upload PDF test**:
   - Mergi pe `/`
   - Upload un PDF de analize
   - Verifică că se salvează în baza de date

3. **Verificare pacient**:
   - Tab "Pacient"
   - Caută CNP-ul
   - Vezi tabelul de evoluție

---

## 🆘 Troubleshooting

### Eroare: "Module not found"
```bash
pip install -r requirements.txt
```

### Eroare: "Tesseract not found"
Asigură-te că Tesseract este instalat:
```bash
# Ubuntu/Debian
apt install tesseract-ocr tesseract-ocr-ron

# Docker - deja inclus în Dockerfile
```

### Eroare: "Database connection failed"
Verifică `DATABASE_URL` în variabilele de mediu.

### Eroare: "File too large"
Crește limita:
```python
# În main.py, adaugă:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    max_age=3600,
)
```

---

## 📝 Backup & Restore

### Export date (MySQL)
```bash
mysqldump -u user -p analize > backup.sql
```

### Import date (MySQL)
```bash
mysql -u user -p analize < backup.sql
```

### Export date (PostgreSQL)
```bash
pg_dump DATABASE_URL > backup.sql
```

---

## 🎉 Finalizare

După deployment, aplicația este accesibilă online la:
- **Railway**: `https://your-app.railway.app`
- **Render**: `https://your-app.onrender.com`
- **VPS**: `https://your-domain.com`

**Succes cu deployment-ul! 🚀**
