# Ghid: Deploy automat cu GitHub + Railway

## Situația actuală

- **Proiectul nu este în Git** – folderul `D:\Ionut analize` nu are repo Git inițializat.
- **Railway** – probabil se face deploy cu `railway up` din acest folder.
- **GitHub** – nu există conexiune cu niciun repository.

## Ce trebuie făcut (o singură dată)

### Pasul 1: Instalare Git (dacă nu e instalat)

1. Descarcă: https://git-scm.com/download/win
2. Instalează cu setările implicite.
3. Restart la CMD/PowerShell după instalare.

### Pasul 2: Creare repository pe GitHub

1. Mergi la: https://github.com/new
2. **Repository name**: `ionut-analize` (sau alt nume)
3. **Visibility**: Public
4. **NU** bifa "Add a README file"
5. Click **Create repository**
6. Copiază URL-ul (ex: `https://github.com/scanaricabinet-ulieru/ionut-analize.git`)

### Pasul 3: Inițializare Git și conectare în proiect

1. Deschide **CMD** în `D:\Ionut analize` (Shift + click dreapta → "Deschide fereastră PowerShell aici")
2. Rulează:

```batch
git init
git add .
git commit -m "Initial - Analize medicale"
git remote add origin https://github.com/TU_USER/TU_REPO.git
git branch -M main
git push -u origin main
```

(Înlocuiește `TU_USER/TU_REPO` cu userul și repo-ul tău, ex: `scanaricabinet-ulieru/ionut-analize`)

3. Dacă cere autentificare, folosește un **Personal Access Token** (Settings → Developer settings → Personal access tokens pe GitHub).

### Pasul 4: Conectare Railway la GitHub

1. Mergi la https://railway.com/dashboard
2. Deschide proiectul **ionut-analize-medicale**
3. Click pe serviciul **ionut-analize-app**
4. Tab **Settings** → **Source**
5. Click **Connect Repo** → alege repository-ul **ionut-analize**
6. Railway va face deploy automat la primul push.

### Pasul 5: Verificare

După push, așteaptă 1–2 minute și deschide:

https://ionut-analize-app-production.up.railway.app

Ar trebui să vezi butonul **Export backup** lângă **Ieșire** (dacă ești logat ca admin).

---

## La fiecare modificare de cod

Rulează **PUSH_SI_DEPLOY.bat** – face push pe GitHub, Railway repornește singur aplicația.

---

## Dacă nu vrei GitHub

Folosește **DEPLOY_BACKUP.bat** (trebuie să fii logat cu `railway login`). Deploy-ul se face direct din folderul local.
