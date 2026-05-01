# Audit: recunoaștere analize din buletine scanate (toate laboratoarele)

Acest document descrie **ce** numără aplicația, **unde** se pierd rânduri între OCR și baza de date, și **cum** investighezi un buletin fără să presupui că fiecare rând tipărit este o analiză.

## Ce este o „analiză” în aplicație

O intrare salvată / afișată ca rezultat corespunde, în general, unui **parametru de laborator cu valoare** (numerică sau calitativă: Negativ, Absenți etc.), eventual cu unitate și interval. Nu sunt analize separate:

- titlurile de secțiune (ex. „BIOCHIMIE”, „Hemoleucogramă completă”);
- notele explicative fără valoare de parametru (ex. disclaimer eGFR pediatru);
- anteturi administrative (adresă laborator, cod probă, dată tipărire);
- rânduri doar cu interval de referință, dacă au fost deja lipite de parametru pe altă logică.

Lista ta manuală de **N parametri** din buletin trebuie comparată cu **numărul de rezultate parsate**, nu cu numărul total de linii din textul OCR.

## Lanțul de procesare (unde se filtrează)

1. **PDF → text** — [`backend/pdf_processor.py`](../backend/pdf_processor.py): PyMuPDF / pdfplumber; dacă e scanat → Tesseract (string + TSV). Calitatea OCR decide cât de multe linii „citibile” există.
2. **Linii → candidat parametru** — [`backend/parser.py`](../backend/parser.py): `_este_linie_parametru` (lungime, exclus administrativ `_linie_este_exclusa`, fragmente în [`administrative_fragments.py`](../backend/administrative_fragments.py), `_este_gunoi_ocr`, etc.).
3. **Candidat → obiect parsat** — reguli pe linie (`_parse_oneline`, Bioclinica, Medlife…).
4. **Filtru final** — în `extract_rezultate`, funcția internă `_add` elimină pseudo-denumiri / zgomot.
5. **Normalizare** — [`backend/normalizer.py`](../backend/normalizer.py): alias → `analiza_standard_id` (nu reduce de obicei numărul de rânduri salvate).

La **Verificare** (debug upload), răspunsul poate include **`audit_linii_text`**: număr linii totale, câte excluse administrativ, câte acceptate ca parametru, câte rezultate după `extract_rezultate`. Dacă `linii_acceptate_ca_parametru` este mare dar `rezultate_extractate` mic, problema e în **parser / lipire linii**; dacă ambele sunt mici, verifică mai întâi **OCR** (text gol, caractere corupte).

### Mai multe buletine sau laboratoare în același PDF

În `audit_linii_text` există **`semnale_multi_buletin_laborator`**:

| Câmp | Rol |
|------|-----|
| `cnp_distincte` / `numar_cnp_distincte` | CNP-uri valide **distincte** (ordinea primei apariții); dacă sunt ≥2, parserul folosește totuși **primul** CNP pentru pacient. |
| `matchuri_cnp_valide_pozitii_unice` | Câte apariții unice (poziție + șir) — antet repetat pe pagini crește numărul fără a însemna neapărat pacienți diferiți. |
| `laboratoare_mentionate_tot_textul` | Rețele recunoscute (**tot** textul), cu `aparitii` și poziții — compară cu laboratorul ales automat (vezi `laborator_rezolvat` în răspunsul Verificare). |
| `pdf_probabil_compus_multi_buletin` | `true` dacă există **mai multe CNP-uri distincte** sau **mai multe mărci** de laborator detectate (nu marchează doar PDF lung cu același lab pe fiecare pagină). |
| `mesaj_scurt` | Recomandare în română (împărțire PDF, override `laborator_id` / `laborator`, verificare OCR la sfârșitul documentului). |

**Detectare laborator pentru normalizare** (`resolve_laborator_id_for_text` în [`backend/lab_detect.py`](../backend/lab_detect.py)) folosește în principal **începutul** textului (~15k caractere) + override-uri. Dacă primul antet e de la un lab iar analizele relevante sunt de la altul (PDF concatenat), aliasurile pot fi suboptimale — folosiți **Verificare** + câmpul laborator din UI sau parametrii query la upload.

Pentru scanare programatică a mărcilor pe tot documentul (fără a rula `extract_rezultate`): `enumerate_lab_brand_mentions` în același modul.

## Cum investighezi un buletin (fără salvare)

1. **Verificare (fără salvare)** din UI sau `POST /upload-async?debug=1` (admin).
2. Deschide în răspuns:
   - **`audit_linii_text`** — sumar linii vs rezultate;
   - **`linii_excluse`** — rânduri marcate administrativ/gunoi la nivel de linie;
   - **`linii_0_80`** / text extras — compară cu PDF-ul sursă.
3. Dacă o linie validă apare la **excluse** sau lipsește din listă: deschide issue / patch în `parser.py` sau `administrative_fragments.py` cu **fixture text** (vezi mai jos), nu doar schimbare ad-hoc.

## Golden set și anti-regresie

### Text-only în git (recomandat)

- Director: [`backend/tests/fixtures/parser_text/`](../backend/tests/fixtures/parser_text/) — `manifest.json` + fișiere `.txt` (ex.: `medlife_like.txt`, `urina_calitativ.txt`, `bioclinica_oneline.txt`, `hemogram_compact.txt`, `ocr_noise_snippet.txt` — text sintetic, fără date reale).
- Teste: `backend/tests/test_parser_text_fixtures.py` (rulează pe CI în workflow-ul „Parser și golden set”).

### Benchmark cu PDF-uri (local; GDPR)

1. Copiați PDF-urile în `samples/golden_pdfs/` (preferabil doar pe mașina locală sau după anonimizare).
2. Porniți de la `scripts/ocr_golden_set.example.json` și creați `scripts/ocr_golden_set.json` — vezi [`GOLDEN_SET_OCR.md`](GOLDEN_SET_OCR.md).
3. Rulați de exemplu:  
   `python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --fail-below 0.90`
4. Anti-regresie cu baseline:  
   `python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --fail-below 0.85 --baseline scripts/golden_baseline.json`  
   (după ce ați generat baseline cu `--write-baseline`).

Rulează testele parser din rădăcina proiectului:

```bash
set PYTHONPATH=.
py -3 -m pytest backend/tests/test_parser_text_fixtures.py backend/tests/test_gaman_luca_bulletin.py -v
```

## LLM Copilot (opțional)

[`backend/llm_buletin_audit.py`](../backend/llm_buletin_audit.py) poate compara extragerea aplicației cu o extragere LLM pentru **verificare încrucișată**. Nu înlocuiește validarea clinică; necesită cheie API și flag-uri în setări. Detalii: `.env.example`.

## Faze ulterioare (nu sunt obligatorii aici)

- Preprocesare imagine (deskew, contrast) înainte de Tesseract — cost și dependențe suplimentare.
- Set mai mare de PDF-uri golden pe CI — doar dacă datele sunt anonimizate și licența o permite.

## Legături utile

| Subiect | Fișier / loc |
|--------|----------------|
| Excludere linii antet | `parser._linie_este_exclusa`, `parser._LINII_EXCLUSE` |
| Gunoi OCR | `parser._este_gunoi_ocr`, `parser._GUNOI_SUBSTR` |
| Corecții OCR pe linie | `ocr_corrections.corecteaza_ocr_linie_buletin` |
| Retry DPI unificat Verificare/Salvare | `main._maybe_retry_ocr_higher_dpi_for_upload` |
| CNP-uri distincte în text | `parser.enumerare_cnp_valide_ordine_aparitie`, `parser.audit_semnale_multi_buletin_laborator` |
| Mărci laborator în tot PDF-ul | `lab_detect.enumerate_lab_brand_mentions` |
| Avertisment la salvare (PDF compus) | `main` după `normalize_rezultate` — mesaj din `audit_semnale_multi_buletin_laborator` |
