# 🚀 GHID IMPLEMENTARE: Activare LLM Learning & Îmbunătățiri OCR

**Versiune:** 1.0  
**Data:** 3 Mai 2026  
**Durata estimată:** 15 minute setup + monitoring  

---

## 📋 Cuprins Rapid

1. ✅ **Activare LLM Learning** (5 min)
2. ✅ **Testare Sistem** (5 min)
3. ✅ **Activare Audit Cross-Check** (2 min)
4. ✅ **Monitoring & Troubleshooting** (5 min)

---

## 🎯 Pasul 1: Activare LLM Learning (5 minute)

### Opțiunea A: Direct Edit .env (Recomandată)

**1. Deschide .env file:**
```bash
# PowerShell:
notepad .env

# Linux/Mac:
nano .env
```

**2. Caută linia:**
```ini
LLM_LEARN_FROM_UPLOAD_ENABLED=false
```

**3. Schimbă în:**
```ini
LLM_LEARN_FROM_UPLOAD_ENABLED=true
```

**4. Salvează fișierul (Ctrl+S)**

---

### Opțiunea B: Python Script (Alternativă)

```bash
# PowerShell:
python check_llm_learning.py --enable

# Output:
# ✅ LLM Learning ENABLED in .env
```

---

### Opțiunea C: Verifica Cheia API

Înainte de a continua, asigură-te că cheia Anthropic Claude e setată:

```bash
# PowerShell:
$env:ANTHROPIC_API_KEY
# Trebuie să arate: sk-ant-...

# Dacă nu e setat, adaugă în .env:
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

---

## 🧪 Pasul 2: Testare Sistem (5 minute)

### 2a. Verificare Status Complet

```bash
# Rulează diagnostic:
python check_llm_learning.py --status

# Output trebuie să arate:
# ✅ llm_learn_from_upload_enabled: True
# ✅ Database tables: analize_standard (2000+), alias_analiza (50+)
# ✅ LLM credentials: WORKING
# ✅ Provider: anthropic
# ✅ Model: claude-haiku-4-5
```

### 2b. Test LLM Call Direct

```bash
python check_llm_learning.py --test-llm-call

# Output:
# Status: success
# ✅ Provider: anthropic
# ✅ Model: claude-haiku-4-5
```

---

### 2c. Test cu PDF Real

Folosește scriptul de diagnostic cu un PDF din buletin:

```bash
# Simplu diagnostic:
python diagnostic_upload_ocr.py samples/buletin_test.pdf

# Cu rezultate:
python diagnostic_upload_ocr.py samples/buletin_test.pdf --show-results

# Cu text OCR:
python diagnostic_upload_ocr.py samples/buletin_test.pdf --show-text --show-results
```

**Output key indicator:**
```
📈 QUALITY ASSESSMENT
  Mapping ratio: 85.0%          # > 70% = Good
  AI Triage Score: 85/100      # > 80% = Excellent
  
🤖 LLM LEARNING SUGGESTIONS
  LLM Learning: ✅ ENABLED
  5 new mappings will be learned from this upload
```

---

## 🔍 Pasul 3: Activare Audit Cross-Check (2 minute)

**Opțional:** Activează validare încrucișată Claude vs Parser

1. **Deschide .env:**
```ini
LLM_BULETIN_AUDIT_ENABLED=true
```

2. **Salvează și restart aplicația**

**Efect:**
- La fiecare upload, Claude va verifica pe paralel ce analize a găsit
- Raport diferențe: analize omise de parser, sau erori de valori
- Vizibil în UI la upload status

---

## 📊 Pasul 4: Monitoring & Troubleshooting

### Monitor Upload Learning Progress

Verifică logs pentru a vedea LLM learning în acțiune:

```bash
# PowerShell - monitorizeaza logs:
Get-Content upload_eroare.txt -Tail 20 -Wait

# Cauta linii cu [UPLOAD-ASYNC]:
# [UPLOAD-ASYNC] llm_learn applied 5 aliases
# [UPLOAD-ASYNC] LLM calls: 7/40
```

---

### Verifica Aliases Salvate în DB

```bash
# PowerShell - SQL query (dacă PostgreSQL):
psql -U postgres -d baza_medicale -c "SELECT * FROM alias_analiza ORDER BY created_at DESC LIMIT 10;"

# Sau din Python:
python -c "
from backend.database import get_cursor
with get_cursor(commit=False) as cur:
    cur.execute('SELECT pattern, analiza_standard_id, scor_match, created_at FROM alias_analiza ORDER BY created_at DESC LIMIT 10')
    for row in cur.fetchall():
        print(row)
"
```

---

### Dashboard Stats (próximas upgrades)

```bash
# (In development) - Verifică progres learning:
curl http://localhost:8000/api/learning-stats
# {
#   "total_uploads": 1250,
#   "aliases_learned": 387,
#   "llm_learning_enabled": true,
#   "accuracy_improvement": "+15%"
# }
```

---

## ⚠️ Troubleshooting

### ❌ Problemă: LLM calls eșuează

**Simptom:**
```
[UPLOAD-ASYNC] ERROR: LLM call failed: 401 Unauthorized
```

**Soluție:**
1. Verifică cheia API:
```bash
echo $env:ANTHROPIC_API_KEY
```
2. Dacă lipsește, adaugă în .env și restart aplicația
3. Testează direct:
```bash
python check_llm_learning.py --test-llm-call
```

---

### ❌ Problemă: OCR returnează text gol

**Simptom:**
```
[UPLOAD-ASYNC] WARNING: No text extracted from PDF
```

**Cauze & Soluții:**

1. **PDF e protejat cu parolă:**
   - Deschide în Adobe Acrobat
   - Exportă fără parolă
   - Re-upload

2. **Tesseract nu e instalat (Windows):**
   ```powershell
   # Instalează din: https://github.com/UB-Mannheim/tesseract/wiki
   # Poi setează în .env:
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   OCR_LANG=ron+eng
   ```

3. **Scan de calitate foarte scăzută:**
   - Reimportă PDF din laborator cu rezoluție mai bună
   - Contactează laboratorul

---

### ❌ Problemă: Alias-uri nu se salvează

**Simptom:**
```sql
SELECT COUNT(*) FROM alias_analiza;  -- Returns 0 (!)
```

**Cauze:**
1. `LLM_LEARN_FROM_UPLOAD_ENABLED=false`
   - Activează și re-upload
2. Score LLM < 86%
   - Scade pragul în .env: `LLM_LEARN_AUTO_APPLY_MIN_SCORE=80.0`
3. Lipsă upload-uri cu analize necunoscute
   - Upload-urile tale au toate analizele în catalog

**Fix rapid:**
```bash
# Import sample aliases de test:
python check_llm_learning.py --import-sample-aliases

# Verificare:
python -c "
from backend.database import get_cursor
with get_cursor(commit=False) as cur:
    cur.execute('SELECT COUNT(*) FROM alias_analiza')
    print(f'Total aliases: {cur.fetchone()[0]}')
"
```

---

## 📈 Metrici de Succes

După 1 săptămână, ar trebui să vezi:

| Metrica | Înainte | După (țintă) |
|---------|---------|--------------|
| Unknown analysis % | 35% | < 10% |
| Mapping ratio | 65% | > 90% |
| LLM aliases saved | 0 | > 100 |
| Upload processing time | 45s | 60-90s |
| Accuracy score | 65% | > 92% |

---

## 🎓 Tips & Best Practices

### ✅ DO:

1. **Upload diverse laboratoare** - Fiecare laborator = noi alias-uri
2. **Monitor logs** - Urmărește progresul learning
3. **Verifica falsuri** - Dacă LLM mapează greșit, corijează manual
4. **Update catalog** - Adaugă noi analize noi în `analize_standard`

### ❌ DON'T:

1. **Nu dezactiva LLM learning** - E gol se setează iar
2. **Nu expune API keys** - Stochează în `.env` (nu commit)
3. **Nu schimbi praguri LLM** - 86% e testat și bun
4. **Nu ignora OCR errors** - Tip: "Failed OCR" = PDF slab

---

## 🔧 Commands Rapide

```bash
# Verificare status
python check_llm_learning.py --status

# Test LLM
python check_llm_learning.py --test-llm-call

# Diagnostic PDF
python diagnostic_upload_ocr.py samples/test.pdf --show-results

# View logs
tail -f upload_eroare.txt

# Count aliases
python -c "from backend.database import get_cursor; import psycopg2; c = get_cursor(commit=False); c.execute('SELECT COUNT(*) FROM alias_analiza'); print(f'Aliases: {c.fetchone()[0]}')"

# Enable LLM
python check_llm_learning.py --enable
```

---

## 📚 Resurse Utile

- **Raport Detaliat:** `RAPORT_DETALIAT_UPLOAD_OCR_LLM.md`
- **Fișier Configurare:** `.env`
- **Database Schema:** `sql/001_schema.sql`
- **Logs:** `upload_eroare.txt`

---

## 🚨 SOS - Contact Support

Dacă ai probleme:

1. Rulează diagnostic:
```bash
python diagnostic_upload_ocr.py <pdf_file> --verbose
python check_llm_learning.py --status
```

2. Colectează logs:
```bash
tail -100 upload_eroare.txt > diagnostic_logs.txt
```

3. Trimite raportul + PDF-ul de test

---

## ✅ Checklist Final

- [ ] `LLM_LEARN_FROM_UPLOAD_ENABLED=true` în .env
- [ ] `ANTHROPIC_API_KEY` setat și valid
- [ ] Test LLM: `python check_llm_learning.py --test-llm-call` ✅
- [ ] Test PDF: `python diagnostic_upload_ocr.py test.pdf` ✅
- [ ] Application restarted
- [ ] Upload test PDF cu analize necunoscute
- [ ] Verifica: alias-uri salvate în DB ✅
- [ ] Monitoring setup: logs monitored

---

**Gata! 🎉 Sistemul e activ și învață din fiecare upload.**

Data viitoare când vei vedea o analiza similară → va fi recunoscută automat!

---

*Generated: 3 Mai 2026*
