# 🏥 Deployment Romarg cPanel - Ghid Complet

## ✅ Ce ai generat:

📦 **deployment_cpanel.zip** (0.08 MB)
- Toate fișierele aplicației
- installer.php (setup automat MySQL)
- .htaccess (configurare server)
- Schema MySQL

📋 **INSTRUCTIUNI_CPANEL.txt**
- Ghid pas cu pas complet

## 🎯 Arhitectură Recomandată: Hibridă

```
┌─────────────────┐         ┌──────────────────┐
│  Railway.app    │────────>│  Romarg Hosting  │
│  (Python/FastAPI)│         │  (MySQL)         │
│  GRATUIT        │         │  Inclus în pachet│
└─────────────────┘         └──────────────────┘
        ↓
    HTTPS automat
    Tesseract OCR inclus
```

### De ce arhitectură hibridă?

**Problema**: Romarg are PHP 7 + MySQL, dar aplicația ta este Python + FastAPI.

**Soluția**:
- ✅ **Railway.app** - rulează Python/FastAPI (GRATUIT)
- ✅ **Romarg MySQL** - stochează datele (deja plătit)
- ✅ **Conexiune** - Railway se conectează la MySQL-ul de pe Romarg

### Avantaje:
- ✓ Python complet funcțional (OCR, FastAPI, toate features)
- ✓ Folosești MySQL-ul Romarg (nu pierzi banii)
- ✓ HTTPS automat pe Railway
- ✓ Zero configurare complexă
- ✓ Backup MySQL pe Romarg (inclus)

---

## 🚀 DEPLOYMENT ÎN 3 PAȘI (10 MINUTE)

### PAS 1: Setup MySQL pe Romarg (3 minute)

#### 1.1 Login cPanel
```
URL: https://cpanel.romarg.ro
User: contul tău Romarg
Pass: parola cPanel
```

#### 1.2 Creează Database MySQL
1. Mergi la: **"MySQL® Databases"**
2. Secțiunea "Create New Database":
   - Nume: `analize` (sau orice nume)
   - Click **"Create Database"**

#### 1.3 Creează User MySQL
1. Secțiunea "MySQL Users":
   - Username: `analize_user`
   - Password: Generează una puternică (ex: `P@ssw0rd!2024`)
   - Click **"Create User"**

#### 1.4 Asociază User cu Database
1. Secțiunea "Add User To Database":
   - User: `analize_user`
   - Database: `analize`
   - Click **"Add"**
2. Pe pagina următoare, bifează **"ALL PRIVILEGES"**
3. Click **"Make Changes"**

#### 1.5 Permite Acces Remote (IMPORTANT!)
1. Mergi la: **"Remote MySQL®"**
2. Adaugă host-uri permise:
   ```
   %.railway.internal
   %.render.com
   %
   ```
3. Click **"Add Host"** pentru fiecare

#### 1.6 Upload installer.php
1. Mergi la: **"File Manager"**
2. Navighează la `public_html`
3. Upload **deployment_cpanel.zip**
4. Click dreapta → **"Extract"**
5. Accesează: `http://your-domain.ro/installer.php`
6. Completează datele MySQL:
   - Host: `localhost` SAU `cpanel.mysql.romarg.ro`
   - Database: `analize`
   - User: `analize_user`
   - Password: [parola ta]
7. Click **"Test Conexiune & Salvează Config"**
8. Click **"Creează Tabelele MySQL"**

✅ MySQL este gata!

**Notează datele de conexiune:**
```
Host: cpanel.mysql.romarg.ro (sau localhost)
Database: analize
User: analize_user
Password: [parola ta]
Port: 3306
```

---

### PAS 2: Deploy Python pe Railway (5 minute)

#### 2.1 Instalare Railway CLI (pe calculatorul tău)

**Windows**:
```powershell
npm install -g @railway/cli
```

Dacă nu ai Node.js:
```powershell
winget install OpenJS.NodeJS.LTS
```

#### 2.2 Login Railway
```bash
railway login
```
→ Se deschide browserul pentru autentificare (cont gratuit)

#### 2.3 Deploy Aplicația
```bash
cd "D:\Ionut analize"
railway init --name analize-medicale
```

#### 2.4 Configurare DATABASE_URL
```bash
railway variables set DATABASE_URL="mysql://analize_user:PAROLA@cpanel.mysql.romarg.ro:3306/analize"
```

⚠️ **Înlocuiește**:
- `PAROLA` → parola MySQL de la Pas 1.3
- `cpanel.mysql.romarg.ro` → host-ul MySQL de la Romarg

**Exemplu real**:
```bash
railway variables set DATABASE_URL="mysql://analize_user:P@ssw0rd!2024@cpanel.mysql.romarg.ro:3306/analize"
```

#### 2.5 Deploy
```bash
railway up
```
→ Așteaptă 2-3 minute (build + deploy)

#### 2.6 Obține URL
```bash
railway domain
```
→ Notează URL-ul (vezi [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md) sau `railway domain`)

✅ Aplicația este LIVE!

---

### PAS 3: Test Final (2 minute)

#### 3.1 Test Health Check
Accesează linkul **Health check** din [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md).

Răspuns așteptat:
```json
{
  "status": "ok",
  "database": "connected"
}
```

#### 3.2 Test Interfață
Accesează linkul **Aplicație (panou medic)** din [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md).

Ar trebui să vezi:
- ✓ Interfața aplicației
- ✓ Tab-uri: Upload, Pacient, Tip Analiză
- ✓ Funcție upload PDF

#### 3.3 Test Upload
1. Click pe **"Upload PDF"**
2. Selectează un PDF de analize
3. Așteaptă procesarea
4. Verifică că apare pacientul în tab **"Pacient"**

✅ **TOTUL FUNCȚIONEAZĂ!**

---

## 📊 Alternative (dacă nu vrei Railway)

### Opțiunea B: Render.com (100% Gratuit)

Similar cu Railway, dar:
- Gratuit permanent
- Se oprește după 15 min inactivitate
- Repornește automat la cerere

**Setup similar**:
1. Push cod pe GitHub
2. Connect repo în Render
3. Add environment: `DATABASE_URL=mysql://...`
4. Deploy automat

### Opțiunea C: Doar Romarg (Dacă ai SSH)

**Necesită**:
- ✓ Acces SSH la server Romarg
- ✓ Python 3.11+ instalat
- ✓ Permisiuni instalare pachete

**Pași** (vezi INSTRUCTIUNI_CPANEL.txt):
1. SSH: `ssh user@server.romarg.ro`
2. Upload fișiere în `~/public_html`
3. `python3 -m venv venv && source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
6. Configurare port în cPanel

---

## 🆘 Troubleshooting

### Eroare: "Can't connect to MySQL server"

**Soluție**:
1. Verifică: Remote MySQL este activat în cPanel
2. Adaugă `%.railway.internal` în whitelist
3. Testează conexiune în installer.php
4. Verifică firewall Romarg

### Eroare: "Access denied for user"

**Soluție**:
1. Verifică username/password sunt corecte
2. Verifică user-ul are ALL PRIVILEGES
3. În cPanel → MySQL Databases → verifică asocierea

### Eroare: "Table doesn't exist"

**Soluție**:
1. Accesează `http://your-domain.ro/installer.php`
2. Click **"Creează Tabelele MySQL"**
3. Sau rulează manual: `mysql -u user -p analize < sql/schema_mysql.sql`

### Railway: "Health check failed"

**Soluție**:
1. Verifică logs: `railway logs`
2. Verifică DATABASE_URL este corect setat
3. Testează conexiune MySQL de pe Railway:
   ```bash
   railway run python test_database.py
   ```

---

## 💰 Costuri

| Serviciu | Cost | Features |
|----------|------|----------|
| **Romarg Hosting** | Deja plătit | MySQL, cPanel, backup |
| **Railway.app** | Gratuit (500h/lună) | Python, PostgreSQL, HTTPS |
| **Total** | 0 lei/lună (față de hosting actual) | Full stack funcțional |

După 500h/lună pe Railway:
- Upgrade la $5/lună (unlimited)
- SAU folosește Render (gratuit permanent dar sleep)

---

## ✅ Checklist Final

- [ ] MySQL creat pe Romarg
- [ ] Remote MySQL activat
- [ ] installer.php rulat cu succes
- [ ] Tabele MySQL create
- [ ] Railway CLI instalat
- [ ] railway login efectuat
- [ ] DATABASE_URL configurat
- [ ] railway up executat
- [ ] `/health` returnează status: ok
- [ ] Interfața se încarcă
- [ ] Upload PDF funcționează

---

## 📞 Suport

**Romarg**:
- Website: https://romarg.ro
- Suport: https://romarg.ro/contact
- cPanel: https://cpanel.romarg.ro

**Railway**:
- Docs: https://docs.railway.app
- Community: https://railway.app/discord
- Status: https://status.railway.app

**Aplicația**:
- Health check: vezi [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md)
- Logs: `railway logs --follow`
- Restart: `railway up`

---

## 🎉 Succes!

Aplicația ta rulează acum:
- ✅ Python FastAPI pe Railway (gratuit)
- ✅ MySQL pe Romarg (deja plătit)
- ✅ HTTPS automat
- ✅ OCR funcțional
- ✅ Toate features active

**URL PUBLIC**: vezi [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md)

🚀 **Aplicația este LIVE!**
