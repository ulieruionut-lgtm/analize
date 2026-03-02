# 🖥️ Deployment Python pe VPS - Ghid Complet
## Opțiunea 2: Server propriu cu control total

═══════════════════════════════════════════════════════════════════════════
  🎯 PREZENTARE GENERALĂ
═══════════════════════════════════════════════════════════════════════════

Această opțiune instalează TOTUL pe un server VPS propriu:
  ✓ Ubuntu 22.04 LTS
  ✓ Python 3.11 + FastAPI
  ✓ MySQL Database
  ✓ Nginx (reverse proxy)
  ✓ SSL/HTTPS (Let's Encrypt)
  ✓ Systemd (pornire automată)
  ✓ Firewall (UFW)

Cost: ~5€/lună (VPS)
Dificultate: Medie (necesită cunoștințe Linux)
Timp setup: 30-60 minute

═══════════════════════════════════════════════════════════════════════════
  📊 RECOMANDĂRI VPS
═══════════════════════════════════════════════════════════════════════════

┌──────────────┬──────────┬─────────┬──────────┬───────────────────────┐
│ Provider     │ RAM      │ Storage │ Cost/lună│ Link                  │
├──────────────┼──────────┼─────────┼──────────┼───────────────────────┤
│ Contabo      │ 4 GB     │ 50 GB   │ 5€       │ contabo.com           │
│ Hetzner      │ 2 GB     │ 20 GB   │ 4€       │ hetzner.com/cloud     │
│ DigitalOcean │ 1 GB     │ 25 GB   │ $6       │ digitalocean.com      │
│ Vultr        │ 1 GB     │ 25 GB   │ $6       │ vultr.com             │
│ OVH          │ 2 GB     │ 20 GB   │ 4€       │ ovhcloud.com          │
└──────────────┴──────────┴─────────┴──────────┴───────────────────────┘

**Recomandare**: Contabo (cel mai ieftin, 4 GB RAM suficient)

═══════════════════════════════════════════════════════════════════════════
  🔧 PARTEA 1: CREARE VPS (10 minute)
═══════════════════════════════════════════════════════════════════════════

## Pasul 1.1: Comandă VPS

### Exemplu Contabo:
1. Mergi la: https://contabo.com/en/vps/
2. Alege: VPS S (4 GB RAM, 50 GB SSD) - 4.99€/lună
3. Region: EU (Germania/Polonia - cel mai aproape de România)
4. OS: Ubuntu 22.04 LTS
5. Adaugă SSH Key (opțional, recomandat)
6. Finalizează comanda

### Exemplu DigitalOcean:
1. Mergi la: https://digitalocean.com
2. Create → Droplets
3. Alege: Basic Plan - $6/lună (1 GB RAM)
4. Region: Frankfurt (aproape de România)
5. Image: Ubuntu 22.04 LTS
6. Add SSH Key (recomandat)
7. Create Droplet

## Pasul 1.2: Notează datele

După creare, vei primi:
```
IP Address: 123.45.67.89
Username: root
Password: [parola temporară]
```

**IMPORTANT**: Schimbă parola la prima conectare!

═══════════════════════════════════════════════════════════════════════════
  🔐 PARTEA 2: CONFIGURARE INIȚIALĂ SERVER (10 minute)
═══════════════════════════════════════════════════════════════════════════

## Pasul 2.1: Conectare SSH

**Windows** (PowerShell):
```powershell
ssh root@123.45.67.89
```

**Windows** (PuTTY):
- Download: https://putty.org
- Host: 123.45.67.89
- Port: 22
- Click "Open"

## Pasul 2.2: Update sistem

```bash
# Update pachete
apt update && apt upgrade -y

# Instalare utilitare de bază
apt install -y curl wget git vim nano htop
```

## Pasul 2.3: Creare user pentru aplicație

```bash
# Creare user (nu lucra ca root!)
adduser analize
# Setează parolă puternică când întreabă

# Adaugă user la sudo
usermod -aG sudo analize

# Schimbă la noul user
su - analize
```

## Pasul 2.4: Configurare Firewall

```bash
# Înapoi la root
exit

# Configurare UFW
ufw allow OpenSSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# Verificare
ufw status
```

═══════════════════════════════════════════════════════════════════════════
  🐍 PARTEA 3: INSTALARE PYTHON 3.11 (5 minute)
═══════════════════════════════════════════════════════════════════════════

```bash
# Instalare Python 3.11
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Verificare versiune
python3.11 --version
# Output: Python 3.11.x

# Set Python 3.11 ca default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

═══════════════════════════════════════════════════════════════════════════
  🖼️ PARTEA 4: INSTALARE TESSERACT OCR (3 minute)
═══════════════════════════════════════════════════════════════════════════

```bash
# Instalare Tesseract + limba română
apt install -y tesseract-ocr tesseract-ocr-ron

# Verificare instalare
tesseract --version
# Output: tesseract 5.x

# Test limba română
tesseract --list-langs | grep ron
# Output: ron
```

═══════════════════════════════════════════════════════════════════════════
  💾 PARTEA 5: INSTALARE MYSQL (5 minute)
═══════════════════════════════════════════════════════════════════════════

```bash
# Instalare MySQL Server
apt install -y mysql-server

# Securizare instalare
mysql_secure_installation
```

**Răspunsuri recomandate**:
```
Set root password? Y
  → Setează parolă puternică pentru MySQL root

Remove anonymous users? Y
Remove test database? Y
Disallow root login remotely? Y
Reload privilege tables? Y
```

## Creare database și user

```bash
# Conectare MySQL
mysql -u root -p
# Introdu parola MySQL root
```

În consola MySQL:
```sql
-- Creare database
CREATE DATABASE analize CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Creare user
CREATE USER 'analize_user'@'localhost' IDENTIFIED BY 'PAROLA_PUTERNICA_AICI';

-- Acordare privilegii
GRANT ALL PRIVILEGES ON analize.* TO 'analize_user'@'localhost';

-- Refresh
FLUSH PRIVILEGES;

-- Ieșire
EXIT;
```

**Notează datele**:
```
Database: analize
User: analize_user
Password: [parola ta]
Host: localhost
Port: 3306
```

═══════════════════════════════════════════════════════════════════════════
  📦 PARTEA 6: DEPLOY APLICAȚIE (10 minute)
═══════════════════════════════════════════════════════════════════════════

## Pasul 6.1: Transfer fișiere pe server

**Variantă A - Git (RECOMANDAT)**:
```bash
# Pe server, ca user analize
cd /home/analize

# Clone repository (dacă ai GitHub)
git clone https://github.com/USERNAME/analize-medicale.git
cd analize-medicale
```

**Variantă B - SCP (fără Git)**:
```powershell
# Pe calculatorul tău (Windows PowerShell)
cd "D:\Ionut analize"

# Compresioneaza
Compress-Archive -Path * -DestinationPath analize.zip

# Upload pe server
scp analize.zip analize@123.45.67.89:/home/analize/
```

Apoi pe server:
```bash
cd /home/analize
unzip analize.zip -d analize-medicale
cd analize-medicale
```

## Pasul 6.2: Instalare dependințe Python

```bash
# Creare virtual environment
python3.11 -m venv venv

# Activare venv
source venv/bin/activate

# Instalare dependințe
pip install --upgrade pip
pip install -r requirements.txt

# Verificare instalare
pip list | grep fastapi
# Ar trebui să vezi fastapi și uvicorn
```

## Pasul 6.3: Configurare .env

```bash
# Creare fișier .env
nano .env
```

Conținut:
```
DATABASE_URL=mysql://analize_user:PAROLA_PUTERNICA_AICI@localhost:3306/analize
OCR_LANG=ron
PDF_TEXT_MIN_CHARS=200
```

Salvează: `Ctrl+X`, `Y`, `Enter`

## Pasul 6.4: Creare tabele database

```bash
# Rulare migrări
python run_migrations.py

# Sau manual cu MySQL
mysql -u analize_user -p analize < sql/schema_mysql.sql
```

## Pasul 6.5: Test aplicație

```bash
# Pornire server test
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# În alt terminal, test
curl http://localhost:8000/health
# Output: {"status":"ok","database":"connected"}
```

Dacă funcționează → `Ctrl+C` pentru a opri

═══════════════════════════════════════════════════════════════════════════
  🔄 PARTEA 7: CONFIGURARE SYSTEMD (pornire automată) (5 minute)
═══════════════════════════════════════════════════════════════════════════

```bash
# Înapoi la root
exit

# Creare serviciu systemd
nano /etc/systemd/system/analize.service
```

Conținut:
```ini
[Unit]
Description=Analize Medicale FastAPI
After=network.target mysql.service

[Service]
Type=simple
User=analize
WorkingDirectory=/home/analize/analize-medicale
Environment="PATH=/home/analize/analize-medicale/venv/bin"
ExecStart=/home/analize/analize-medicale/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activare serviciu
systemctl daemon-reload
systemctl enable analize
systemctl start analize

# Verificare status
systemctl status analize
# Ar trebui să vezi: active (running)

# Logs
journalctl -u analize -f
```

═══════════════════════════════════════════════════════════════════════════
  🌐 PARTEA 8: CONFIGURARE NGINX (reverse proxy) (10 minute)
═══════════════════════════════════════════════════════════════════════════

## Pasul 8.1: Instalare Nginx

```bash
apt install -y nginx
systemctl enable nginx
systemctl start nginx
```

## Pasul 8.2: Configurare Nginx

```bash
# Creare configurare site
nano /etc/nginx/sites-available/analize
```

Conținut:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Schimbă cu domeniul tău!

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (dacă e necesar)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Activare site
ln -s /etc/nginx/sites-available/analize /etc/nginx/sites-enabled/

# Test configurare
nginx -t

# Restart Nginx
systemctl restart nginx
```

## Pasul 8.3: Test acces

```bash
# Test local
curl http://localhost/health

# Test de pe calculator
# Accesează în browser: http://123.45.67.89/health
```

═══════════════════════════════════════════════════════════════════════════
  🔒 PARTEA 9: CONFIGURARE SSL/HTTPS (5 minute)
═══════════════════════════════════════════════════════════════════════════

**Condiție**: Trebuie să ai un domeniu (ex: analize.yourdomain.com)

```bash
# Instalare Certbot
apt install -y certbot python3-certbot-nginx

# Obținere certificat SSL (înlocuiește domeniul!)
certbot --nginx -d your-domain.com

# Urmează prompturile:
# Email: your@email.com
# Agree to terms: Yes
# Share email: No (opțional)
# Redirect HTTP to HTTPS: Yes (recomandat)

# Test renewal automat
certbot renew --dry-run
```

Acum aplicația este accesibilă la: **https://your-domain.com** 🎉

═══════════════════════════════════════════════════════════════════════════
  📊 PARTEA 10: MONITORING & MAINTENANCE
═══════════════════════════════════════════════════════════════════════════

## Comenzi utile

```bash
# Status aplicație
systemctl status analize

# Restart aplicație
systemctl restart analize

# Logs aplicație (real-time)
journalctl -u analize -f

# Logs Nginx
tail -f /var/log/nginx/error.log

# Verificare spațiu disk
df -h

# Verificare RAM
free -h

# Procese active
htop
```

## Backup automat MySQL

```bash
# Creare script backup
nano /home/analize/backup.sh
```

Conținut:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/analize/backups"
mkdir -p $BACKUP_DIR

mysqldump -u analize_user -pPAROLA_AICI analize > $BACKUP_DIR/analize_$DATE.sql
gzip $BACKUP_DIR/analize_$DATE.sql

# Păstrează doar ultimele 7 zile
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

```bash
# Permisiuni execuție
chmod +x /home/analize/backup.sh

# Configurare cron (backup zilnic la 2 AM)
crontab -e
```

Adaugă linia:
```
0 2 * * * /home/analize/backup.sh
```

═══════════════════════════════════════════════════════════════════════════
  🆘 TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════

### Aplicația nu pornește

```bash
# Verifică logs
journalctl -u analize -n 50

# Verifică permisiuni
ls -la /home/analize/analize-medicale

# Test manual
cd /home/analize/analize-medicale
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Eroare MySQL connection

```bash
# Test conexiune MySQL
mysql -u analize_user -p analize

# Verifică .env
cat /home/analize/analize-medicale/.env

# Verifică MySQL running
systemctl status mysql
```

### Nginx erori

```bash
# Test configurare
nginx -t

# Logs
tail -f /var/log/nginx/error.log

# Restart
systemctl restart nginx
```

═══════════════════════════════════════════════════════════════════════════
  ✅ VERIFICARE FINALĂ
═══════════════════════════════════════════════════════════════════════════

Checklist:
□ VPS creat și accesibil via SSH
□ Python 3.11 instalat
□ Tesseract OCR instalat + limba română
□ MySQL instalat și configurat
□ Database și user create
□ Aplicație deployed în /home/analize
□ Dependințe Python instalate
□ .env configurat corect
□ Tabele MySQL create
□ Systemd service activ (systemctl status analize)
□ Nginx instalat și configurat
□ SSL/HTTPS activat (certbot)
□ Test health: https://your-domain.com/health
□ Test upload PDF funcționează
□ Backup automat configurat

═══════════════════════════════════════════════════════════════════════════
  🎉 FINALIZARE
═══════════════════════════════════════════════════════════════════════════

Aplicația ta rulează acum pe:
  🌐 URL: https://your-domain.com
  🖥️  Server: VPS propriu (control total)
  💾 Database: MySQL local (fast)
  🔒 HTTPS: Let's Encrypt (gratuit)
  🔄 Backup: Zilnic automat
  💰 Cost: ~5€/lună

Succes! 🚀
