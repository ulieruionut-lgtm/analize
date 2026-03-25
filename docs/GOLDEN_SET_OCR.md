# Golden Set OCR - setup rapid

## 1) Pune PDF-urile etalon

- Copiaza PDF-urile in `samples/golden_pdfs/`.
- Recomandat: minim 15-30 buletine mixte (text + scan), din laboratoare diferite.

## 2) Defineste expected (format hibrid)

- Pleci de la `scripts/ocr_golden_set.example.json`.
- Creezi un fisier nou, de exemplu `scripts/ocr_golden_set.json`.
- Pentru fiecare caz:
  - completezi `pdf` cu path relativ (ex: `samples/golden_pdfs/nitu_2026-02-13.pdf`)
  - completezi `expected` cu analizele validate (denumire + valoare/valoare_text + unitate)

Exemplu:

```json
{
  "cases": [
    {
      "pdf": "samples/golden_pdfs/nitu_2026-02-13.pdf",
      "expected": [
        {"denumire": "Hemoglobina", "valoare": 13.3, "unitate": "g/dL"},
        {"denumire": "Creatinina serica", "valoare": 0.27, "unitate": "mg/dL"}
      ]
    }
  ]
}
```

## 3) Ruleaza benchmark-ul

Comparatie pe denumire (mai permisiv, util in primele iteratii):

```bash
python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --fail-below 0.90
```

Comparatie stricta (denumire + valoare + unitate):

```bash
python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.json --strict-values --fail-below 0.90
```

### Folder alternativ (`input/` + `expected/`)

Poți folosi `tests/golden_set/input/*.pdf` și `tests/golden_set/expected/<același_nume>.json` (JSON = listă de analize sau `{"expected": [...]}`). În fiecare rând poți folosi fie `denumire` / `valoare` / `unitate`, fie `analyte` / `value` / `unit` / `category` (category nu intră în cheia strictă de comparare).

```bash
python scripts/verifica_parser_pdf.py --golden-dir tests/golden_set --fail-below 0.85
```

### Anti-regresie (baseline)

După un run bun, salvezi scorul:

```bash
python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.real_v1.json --fail-below 0 --write-baseline scripts/golden_baseline.json
```

La commituri ulterioare:

```bash
python scripts/verifica_parser_pdf.py --golden scripts/ocr_golden_set.real_v1.json --fail-below 0.85 --baseline scripts/golden_baseline.json
```

- Cod **2**: F1 sub `--fail-below`
- Cod **3**: F1 mai mic decât în baseline (regresie)

### Coduri de ieșire

| Cod | Semnificație        |
|-----|---------------------|
| 0   | OK                  |
| 1   | Eroare input/fișier |
| 2   | F1 < prag           |
| 3   | F1 < baseline       |

## 4) Interpretare rezultat

- `Precision`: cate rezultate extrase sunt corecte.
- `Recall`: cate rezultate corecte din PDF au fost gasite.
- `F1`: scor combinat precision/recall.
- `NeedsReviewRate`: procent rezultate marcate pentru verificare manuala.

Tinta recomandata pentru productie:
- F1 >= 0.99 pe set etalon stabil
- NeedsReviewRate controlat (de ex. 5-15%, in functie de calitatea scan-urilor)
