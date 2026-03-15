# Pași pentru verificare deploy Railway

## Ce s-a corectat

1. **Healthcheck timeout** – mărit de la 100 la 180 secunde (Railway așteaptă mai mult până când aplicația răspunde)
2. **Conectare DB la pornire** – redus de la 5×2s la 3×1s în caz de eșec

## Pași pentru tine

### 1. Push modificările
Asigură-te că ai făcut push:
```bash
git add railway.json backend/main.py
git commit -m "fix: healthcheck timeout 180s, DB connect mai rapid"
git push origin main
```

### 2. În Railway Dashboard
- Mergi la **Deployments** pentru serviciul **web**
- Așteaptă noul deploy (după push de pe GitHub)
- Verifică dacă starea este **SUCCESS** (verde) în loc de **FAILED**

### 3. Dacă tot eșuează – trimite din Railway
- **View logs** la ultimul deploy
- Copiază ultimele 50–100 rânduri din log (unde apar erori sau `[STARTUP]`)
- Trimite-le aici pentru analiză

### 4. După deploy reușit
- Deschide https://web-production-2a2ad.up.railway.app
- Fă **Ctrl+F5** (reîmprospătare forțată)
- Loghează-te ca **admin**
- Mergi la **Setări**
- Derulează în cardul **Backup baza de date**
- Ar trebui să vezi sub backup secțiunea **Import dictionar analize (Excel)** cu cele 2 butoane
