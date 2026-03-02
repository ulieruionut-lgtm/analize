# Plan de implementare – Sistem analize medicale (PDF → DB)

## Scop
Aplicație care: primește PDF-uri cu analize, detectează tipul (text/scan), extrage CNP + nume + rezultate, normalizează parametrii și salvează în PostgreSQL. Medicul poate consulta analizele după CNP/Nume și indici (fără autentificare în MVP).

---

## Tehnologii alese (validat)

| Componentă      | Tehnologie   | Motiv |
|-----------------|-------------|--------|
| Backend         | Python 3.11 + FastAPI | Rapid, async, OpenAPI automat |
| Bază de date    | PostgreSQL  | Relații, JSON dacă e nevoie, fiabil |
| Extragere text  | pdfplumber  | Bun pentru PDF-uri text, simplu |
| OCR             | Tesseract (pytesseract) | Local, fără API extern, suport RO |
| Frontend MVP    | HTML simplu + form upload | Minim pentru testare; UI mai frumos după |

**Alternativă „mai simplă” (AI):** Poți folosi ulterior un LLM (ex. API OpenAI/Claude) doar pentru **parsare** (extrage CNP, nume, liste parametru–valoare din text brut). Nu înlocuiește OCR; doar transformă textul extras în structură. Recomandare: începi cu reguli (regex + parser) pentru cost zero și predictibilitate; AI îl adaugi opțional ca fallback pentru formulare foarte neobișnuite.

---

## Structură proiect (MVP)

```
Ionut analize/
├── PLAN_IMPLEMENTARE.md          # acest document
├── backend/
│   ├── main.py                   # FastAPI app, rute /upload, /pacient/{cnp}
│   ├── config.py                 # setări (DB, limite text/OCR)
│   ├── pdf_processor.py          # detectare tip PDF + extragere text
│   ├── ocr_processor.py          # Tesseract pe pagini
│   ├── parser.py                 # CNP, nume, parametri (regex + reguli)
│   ├── normalizer.py             # mapare alias → analiza_standard
│   ├── database.py               # conexiune, tabele, CRUD
│   ├── models.py                 # Pydantic + descrieri tabele
│   └── schemas.py                # DTO-uri API (upload response, pacient, analize)
├── sql/
│   ├── 001_schema.sql            # CREATE TABLE
│   └── 002_seed_analize_standard.sql  # date inițiale analize standard + alias
├── frontend/                     # opțional MVP
│   └── index.html                # form upload + afișare rezultat
├── requirements.txt
├── .env.example
└── README.md
```

---

## Etape de implementare (ordine clară)

### ETAPA 1 – Mediu și schemă DB (ziua 1)
- [ ] Python 3.11, venv, `pip install -r requirements.txt`
- [ ] PostgreSQL instalat local; creare DB (ex. `analize_medicale`)
- [ ] Rulare `sql/001_schema.sql` + `002_seed_analize_standard.sql`
- [ ] Configurare `.env`: `DATABASE_URL`, eventual `OCR_LANG=ron`
- [ ] Test conexiune din `database.py`

### ETAPA 2 – Detectare tip PDF și extragere text (ziua 2)
- [ ] `pdf_processor.py`: folosire pdfplumber pentru extragere text
- [ ] Prag: dacă `len(text) > 200` → considerăm PDF text; altfel → OCR
- [ ] `ocr_processor.py`: pytesseract pe pagini (PDF → imagine → text)
- [ ] Unificare: o singură funcție „extrage text din PDF” (text + OCR fallback)

### ETAPA 3 – Extragere CNP și Nume (ziua 3)
- [ ] **CNP:** regex `\b[1-8]\d{12}\b` + validare cifră control (constanta 279146358279)
- [ ] **Nume:** patternuri „Nume:”, „Pacient:”, „Beneficiar:”, eventual prima linie relevantă
- [ ] Salvare: nume complet; opțional split prenume/nume (spatiu sau virgulă)
- [ ] Funcție în `parser.py`: `extract_patient(text) -> {cnp, nume, prenume?}`

### ETAPA 4 – Normalizare analize (cheie pentru categorii)
- [ ] Tabel `analiza_standard`: id, cod_standard, denumire_standard
- [ ] Tabel `analiza_alias`: id, analiza_standard_id, alias
- [ ] `normalizer.py`: „găsește parametru în text” → caută în alias → returnează analiza_standard_id sau None (necategorizat)
- [ ] Seed: minim 5–10 analize frecvente (Glicemie, Hb, WBC, etc.) + alias-uri

### ETAPA 5 – Parsare rezultate analize (ziua 4–5)
- [ ] Parser generic: linii tip „Denumire parametru  valoare  unitate  [interval]”
- [ ] Regex / reguli pentru: parametru, valoare numerică, unitate, interval min–max, flag (H/L etc.)
- [ ] Pentru fiecare parametru găsit: apel normalizer → obține analiza_standard_id
- [ ] Output: listă `{analiza_standard_id, valoare, unitate, interval_min, interval_max, flag}`

### ETAPA 6 – Integrare și salvare (ziua 5–6)
- [ ] Flux în `main.py`: Upload PDF → pdf_processor → parser (CNP, nume, rezultate) → normalizer → database
- [ ] Inserare/actualizare: pacienti (după CNP), buletine (pacient_id, laborator, fișier), rezultate_analize
- [ ] Endpoint `POST /upload`: primește fișier, returnează pacient + număr analize salvate
- [ ] Endpoint `GET /pacient/{cnp}`: returnează pacienti + buletine + rezultate (pentru medic)

### ETAPA 7 – Frontend minim (ziua 6–7)
- [ ] Pagină HTML: form upload PDF, afișare mesaj succes/eroare
- [ ] Opțional: link către „Vezi pacienti” sau căutare după CNP (GET pe API)

### ETAPA 8 – Testare MVP
- [ ] 2–3 PDF-uri reale (unul text, unul scan dacă e posibil)
- [ ] Verificare în DB: `SELECT * FROM pacienti;` și `rezultate_analize`
- [ ] Test `GET /pacient/{cnp}` cu date corecte

---

## După ce MVP funcționează (ulterior)
- Autentificare (medic)
- GDPR: consimțământ, retenție, export, ștergere
- Docker + deploy (AWS/Azure/DigitalOcean)
- SSL, backup, criptare

---

## Rezumat ordine lucru (săptămâna 1)
1. Mediu + PostgreSQL + schema + seed analize standard.
2. Extragere text din PDF (pdfplumber + OCR fallback).
3. Parser CNP + Nume + validare CNP.
4. Normalizare parametri (alias → standard).
5. Parser rezultate (parametru, valoare, unitate, interval).
6. Integrare upload + salvare + `GET /pacient/{cnp}`.
7. Frontend minim upload.
8. Testare cu PDF-uri reale.

Dacă ești de acord cu acest plan, următorul pas concret este: **crearea structurii de foldere, requirements.txt și a fișierelor sql + schelet pentru backend** ca să poți rula primul `uvicorn main:app --reload` și prima migrare DB.
