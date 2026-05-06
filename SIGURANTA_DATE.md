# Siguranța datelor – Analize Medicale

## De ce se șterg datele la redeploy pe Railway?

Aplicația poate folosi două tipuri de bază de date:

| Tip | Comportament | Persistență la redeploy |
|-----|--------------|-------------------------|
| **SQLite** | Fișier `analize.db` în container | **NU** – datele se pierd |
| **PostgreSQL** | Bază de date externă Railway | **DA** – datele persista |

Dacă datele dispar la fiecare redeploy, probabil **PostgreSQL nu este configurat** sau aplicația folosește SQLite (fallback când `DATABASE_URL` lipsește).

---

## 1. Configurare PostgreSQL pe Railway

### Pași

1. Deschide **Railway Dashboard** → proiectul tău
2. Click **"+ New"**
3. Alege **"Database"** → **PostgreSQL**
4. Așteaptă 30–60 secunde – Railway creează baza
5. Railway setează automat variabila **`DATABASE_URL`** și o leagă de aplicație
6. La următorul deploy, aplicația va folosi PostgreSQL și datele vor persista

### Verificare

În terminal (cu Railway CLI):

```bash
railway variables
```

Trebuie să existe `DATABASE_URL` cu valoare de tip `postgresql://...`

### Dacă tabelele lipsesc (eroare "relation does not exist")

Deschide în browser: **baza URL** din [RAILWAY_PRODUCTION.md](RAILWAY_PRODUCTION.md) (coloana „Aplicație”) + sufixul **`/api/migrate`** — doar dacă știi ce face; în producție restricționează accesul.

Acest endpoint rulează migrările și creează tabelele. După ce se încarcă, reîncearcă upload-ul PDF.

---

## 2. Backup manual înainte de redeploy

Indiferent de baza de date, este recomandat să faci backup regulat:

1. Intră în aplicație ca **admin**
2. Click **"Export backup"** (în header sau în Setări → Backup)
3. Se descarcă fișierul `analize_backup_YYYYMMDD_HHMM.json`
4. Păstrează fișierul în siguranță (pe calculator, cloud etc.)

**Recomandare:** Exportă backup **înainte** de fiecare redeploy sau la intervale regulate.

---

## 3. Restore din fișierul JSON

Dacă ai pierdut date, poți recupera din ultimul backup exportat:

1. Intră în aplicație ca **admin**
2. Mergi la **Setări** → secțiunea **Backup baza de date**
3. Click **"Importă backup"**
4. Selectează fișierul JSON exportat anterior
5. Datele din fișier vor fi **adăugate** peste cele existente (nu se șterg datele curente)

**Notă:** Restore-ul adaugă pacienți, buletine și rezultate. Pacienții duplicați (același CNP) sunt actualizați, nu dublați.

---

## 4. Ce să faci dacă ai pierdut date

1. Verifică dacă ai un fișier backup (`analize_backup_*.json`) salvat
2. Dacă da: folosește **Importă backup** din Setări
3. Dacă nu: datele nu pot fi recuperate – configura **PostgreSQL** pentru viitor și fă backup regulat
4. Adaugă PostgreSQL pe Railway (vezi secțiunea 1) pentru a evita pierderea datelor la redeploy

---

## Rezumat

- **PostgreSQL pe Railway** = datele persistă la redeploy
- **Export backup** = siguranță în caz de problemă
- **Import backup** = recuperare din fișierul JSON exportat
