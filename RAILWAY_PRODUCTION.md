# Producție Railway — sursă unică (centralizat)

Acest fișier este **singura referință** pentru URL-ul live și modul de deploy folosit în producție. Alte fișiere din repo pot conține URL-uri vechi; le ignori în favoarea acestui document.

## URL public

| Ce | Link |
| --- | --- |
| **Aplicație (panou medic)** | [https://analize-production.up.railway.app/](https://analize-production.up.railway.app/) |
| **Health check** | [https://analize-production.up.railway.app/health](https://analize-production.up.railway.app/health) |

## Proiect pe Railway (conform dashboard)

- **Proiect:** `soothing-fascination`
- **Mediu:** `production`
- **Serviciu:** `analize`
- **Domeniu generat:** `analize-production.up.railway.app`
- **Regiune (exemplu din deploy):** `europe-west4-drams3a`

## Variabile mediu — Claude Haiku (Copilot audit + sugestii alias)

Aceleași variabile ca în `.env` local; pe Railway le setezi în **Dashboard → serviciul `analize` → Variables** sau din CLI (din folderul proiectului, cu `railway link` deja făcut):

| Variabilă | Valoare tipică |
| --- | --- |
| `LLM_BULETIN_AUDIT_ENABLED` | `true` |
| `LLM_PROVIDER` | `anthropic` |
| `LLM_MODEL` | `claude-haiku-4-5` (opțional; implicit în cod) |
| `ANTHROPIC_API_KEY` | cheia din [Anthropic Console](https://console.anthropic.com/) (secret) |

**CLI (exemplu — cheia NU în linia de comandă):**

```bash
railway variable set LLM_BULETIN_AUDIT_ENABLED=true LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5 -e production -s analize
# Cheia: din fișier sau clipboard, fără a o lipi în terminal vizibil:
#   type .env | findstr ...   # evită; preferă Dashboard sau:
echo "CHEIA_TA" | railway variable set ANTHROPIC_API_KEY --stdin -e production -s analize
```

După modificarea variabilelor, Railway redeployează automat (sau rulezi `railway up` / aștepți deploy-ul din Git).

## Cum se face deploy

- **Manual din CLI:** `railway up` (din folderul proiectului, cu CLI logat și proiect legat).
- Nu depinde de acest document faptul că folosești sau nu deploy automat din GitHub; important e să rulezi deploy pe serviciul corect după ce faci push.

## Comenzi utile

```bash
railway login
railway link          # dacă trebuie să legi folderul de proiectul Railway
railway domain        # confirmă URL-ul public
railway logs          # erori / pornire aplicație
railway restart
```

## Local vs producție

| Mediu | URL |
| --- | --- |
| Dezvoltare | http://localhost:8000 |
| Producție | Vezi tabelul de mai sus (coloana **Link**) |

## Ghiduri din repo

Fișierele `*.md` și `*.txt` cu pași Railway au fost aliniate astfel: **nu mai hardcodează domenii de tip `analize-xxx` sau proiecte vechi**; trimit la acest document sau la `railway domain`. Rămân mențiuni istorice (ex. `zestful-truth`, ID-uri vechi de proiect) doar ca context în note de tip „istoric”.

---

*Ultima aliniere la setup-ul din Railway dashboard (serviciu **analize**, domeniu **analize-production**).*
