# Actualizări automate: GitHub → Railway

## Ce înseamnă „automat” aici

1. **GitHub** primește cod nou când faci `git push` (sau merge în `main` din PR).
2. **Railway** redeployează **singur** dacă proiectul e legat de acel repo GitHub și branch-ul de producție e `main`.

Nu e nevoie de FTP sau copiere manuală a fișierelor pe server.

## Pașii în Railway (o singură dată)

1. Deschide proiectul în [Railway](https://railway.app/).
2. Serviciul care rulează API-ul (FastAPI) → **Settings** → **Source**.
3. **Connect Repo** → alege `ulieruionut-lgtm/analize` (sau repo-ul tău).
4. Setează **Root Directory** dacă aplicația e într-un subfolder (ex. `Ionut analize`).
5. **Branch de deploy**: `main`.
6. Salvează. De acum, **fiecare push pe `main`** declanșează build + deploy.

## Verificare după deploy

- **`GET /health`** → `parser_version` trebuie să coincidă cu constanta din `backend/main.py` (`_PARSER_VERSION`).
- **Interfața**: în header, versiunea afișată e legată de același marcator (+ opțional `BUILD_VERSION` din imagine, dacă e diferit).

## GitHub Actions (repo-ul tău)

- **`ci-main-smoke.yml`**: la push/PR pe `main`, rulează import smoke (prinde erori gen `No module named …`).
- **`parser-golden.yml`**: rulează doar când se schimbă fișiere din `backend/` sau golden set (benchmark opțional).

Workflow-ul **nu** înlocuiește integrarea Railway–GitHub; doar validează codul înainte/side-by-side.

## Opțional: deploy și din GitHub Actions

Dacă vrei deploy explicit din Actions (în loc sau în plus față de integrarea Railway):

1. În Railway: **Account** → **Tokens** → creează token.
2. În GitHub repo: **Settings → Secrets and variables → Actions**:
   - `RAILWAY_TOKEN`
   - eventual `RAILWAY_SERVICE_ID` / proiect (depinde de CLI).
3. Adaugă un job cu [Railway CLI](https://docs.railway.app/guides/cli) sau acțiunea oficială — documentația Railway se schimbă; verifică ghidul actual.

În practică, **legarea repo-ului în Railway** e suficientă pentru majoritatea cazurilor.
