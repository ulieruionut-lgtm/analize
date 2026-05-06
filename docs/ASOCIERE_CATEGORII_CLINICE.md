# Asociere pe categorii (ghid clinic → cod)

## Unde e implementat

| Componentă | Rol |
|------------|-----|
| `backend/analiza_categorii.py` | `categorie_grup_pentru_cod(cod)` → etichetă pentru dropdown „Analize necunoscute”; `potrivire_categorie_pdf_cu_grup` aliniază secțiunea PDF cu grupul. |
| `backend/parser.py` | `_SECTIUNI` detectează antetele (Biochimie, Microbiologie, ENDOCRINOLOGIE, …) → `RezultatParsat.categorie`. |
| `backend/normalizer.py` | Aliasuri din DB + filtru gunoi înainte de log necunoscute. |

## Clasificare actuală (rezumat)

- **Hormoni tiroidieni**: TSH, FT3, FT4, anti-TPO, etc. (FT4 **nu** mai e la Biochimie în UI.)
- **Hormoni (endocrinologie)**: FSH, LH, cortizol, insulină, …
- **Biochimie / metabolism**: ALT/AST, bilirubină, glucoză, feritină, eGFR (EGFR), creatinină, …
- **Hematologie**: VSH, hemogramă, …
- **Examen urină**: parametri `_U`, mucus urinar dacă codul e `MUCUS_U` / conține `URIN`.
- **Microbiologie / infecțioase**: fragmente în cod (UROCULT, CHLAMYD, CULTURA, CANDIDA, …) + coduri dedicate dacă le adaugi în catalog.

## Aliasuri noi pentru PDF

Adaugă în `analiza_alias` (sau migrare SQL) denumirile exacte din laborator, mapate la `analiza_standard_id` existent. Exemple utile:

- `FT4 – Tiroxină serică liberă` → FT4  
- `Glucoză` / `Glicemie` → `GLUCOZA` sau `GLUCOZA_FASTING`  
- `RFG` / `eGFR` → `EGFR`  

## Valori pure (nu analize)

Texte de tip „Negativ”, „Nu s-a detectat”, „Culturi bacteriene absente” sunt tratate ca **rezultat**, nu ca nume de analiză (`_RE_REZULTAT_PUR` / gunoi).

## Zgomot administrativ

Observații, cod parafă/formular, data tipăririi, antet tabel „ANALIZE REZULTATE INTERVAL…” → excluse ca parametri (`_LINII_EXCLUSE`).

## Scripturi

- `curatare_gunoi_pipeline.py` — curăță lista necunoscute + opțional rezultate nemapate.
- Rulează cu Python din `venv` sau `pip install -r requirements.txt`.
