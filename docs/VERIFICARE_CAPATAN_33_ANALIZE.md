# Verificare: 33 / 49 analize (manual) vs ~28 (aplicație)

## Rapoarte **Affidea / Hiperdia** (ex. Capatan)

În buletin, pe **toate rândurile din tabele** sunt **~49 de poziții** (hematologie 24 + biochimie 7 + creatinină+RFG 2 + urină 12 + imunologie 4).

- **33** = număr frecvent folosit dacă grupezi perechi (ex. % + absolut) sau nu numeri fiecare sub-rând.
- **28** = câte reușește parserul să extragă din textul PDF (înainte de ultimele îmbunătățiri).

Îmbunătățiri în cod: `page.get_text(sort=True)` în PyMuPDF (ordine corectă în tabele multi-pagină) + antete **ANALIZA DE URIN**, **SEDIMENT URIN**, **CREATININA** pentru categorii.

### Export JSON / listă (local, fără server)

Din rădăcina proiectului, cu venv activat:

```powershell
cd "d:\Ionut analize"
python scripts/verifica_parser_pdf.py "C:\cale\Capatan Luminita.pdf" --json capatan_parsat.json
python scripts/verifica_parser_pdf.py "C:\cale\Capatan Luminita.pdf" --list capatan_extrase.txt
```

Compară cu lista ta de referință:

```powershell
python scripts/diff_analize_liste.py capatan_extrase.txt lista_referinta.txt --fuzzy
```

---

# Verificare: 33 analize (manual) vs ~28 (aplicație)

## Pasul 1 — Copiază din aplicație cele 28 de denumiri

1. Deschide pacientul **Capatan** → tabelul cu analize.
2. Selectează toate denumirile din prima coloană (sau export mental) și pune **câte o denumire pe linie** într-un fișier `din_app.txt`.

## Pasul 2 — Lista ta de referință (din PDF)

Pune **câte o denumire pe linie** în `din_pdf.txt` (exact cum apar în buletin sau cum le-ai notat tu).

## Pasul 3 — Compară automat

Din rădăcina proiectului:

```bash
python scripts/diff_analize_liste.py din_pdf.txt din_app.txt
```

Vei vedea:
- **Doar în PDF** → candidați pentru „lipsă din app” (cei ~5)
- **Doar în app** → extrase dar nu în lista ta (denumiri diferite / OCR)

## Lista ta anterioară (referință — 33 poziții)

Poți folosi ca punct de plecare pentru `din_pdf.txt` (editează după buletinul real):

### Hemogramă / hematologie
- VSH  
- Hematii  
- Hemoglobina  
- Hematocrit  
- Trombocite  
- Leucocite  
- Neutrofile %  
- Neutrofile (absolut)  
- Eozinofile %  
- Eozinofile (absolut)  
- Bazofile %  
- Bazofile (absolut)  
- Limfocite %  
- Limfocite (absolut)  
- Monocite %  
- Monocite (absolut)  
- VEM (MCV)  
- HEM (MCH) — uneori OCR  
- CHEM (MCHC) — uneori OCR  
- MPV  
- RDW  
- PDW  
- P-LCR  
- PCT  

### Biochimie
- Fosfatază alcalină  
- Glicemie a jeun  
- Proteina C reactivă cantitativ  
- Sideremie  
- TGO / AST  
- TGP / ALT  
- Transferină  

### Funcție renală
- Creatinină serică  
- RFG (eGFR)  

### Urină
- pH  
- Densitate  
- Proteine  
- Glucoză  
- Corpi cetonici  
- Urobilinogen  
- Bilirubină  
- Leucocite (urină)  
- Hematii (urină)  
- Nitriți  
- Sediment: Celule epiteliale  
- Sediment: Leucocite  

### Imunologie / hormoni
- Feritină  
- FT4  
- TSH  
- Vitamina B12  

---

## De ce lipsesc adesea 3–5 din cele 33 (fără să fie „bug”)

| Situație | Explicație |
|----------|------------|
| **RFG + creatinină** | Uneori sunt pe același rând sau RFG e calcul într-un bloc interpretare → o singură linie parsată. |
| **Sediment (2 rânduri)** | „Celule epiteliale” / „Leucocite” sub sediment pot fi într-un paragraf sau tabel greu de tăiat în linii. |
| **HEM / CHEM** | În PDF pot fi etichetate MCH/MCHC; dacă numeri și varianta OCR și standardul, dublezi numerotarea. |
| **Leucocite / Hematii** | În sânge și urină: în app sunt două rânduri dacă textul diferă; la numărare manuală le poți număra de 2×2. |
| **Deduplicare parser** | Două linii identice (denumire + valoare + categorie) → una singură în listă. |

---

## După ce ai lista „Doar în PDF”

Trimite acele **denumiri exacte** (copy-paste din PDF) pentru a le lega de reguli în `parser.py` sau de **aliasuri** în aplicație.
