# Raport comparație: Mandache – PDF 19.02.2026 vs DB

## Format PDF (Bioclinica, "VALORI ANTECEDENT")

PDF-ul are coloane: **Valoare curentă** | **Interval referință** | **Valoare antecedentă (dată)**  
Ex: `Hematii 4.460.000 /mm³ (4.010.000 - 5.290.000) 3.530.000` = valoare 4.460.000, interval, antecedent 3.530.000

---

## Comparație parametru cu parametru

| Parametru | PDF (valoare) | În DB? | Notă |
|-----------|---------------|--------|------|
| **Hematii** | 4.460.000 /mm³ | ⚠️ Greșit | Asociere: "Hemoleucogramă" → text Hematii; valoarea 4.460.000 nu e extrasă corect |
| **Hemoglobină** | 13,6 g/dL | ❌ Lipsă | |
| **Hematocrit** | 41,1 % | ❌ Lipsă | |
| **MCV** | 92,1 fL | ❌ Lipsă | |
| **MCH** | 30,6 pg | ❌ Lipsă | |
| **MCHC** | 33,2 g/dL | ❌ Lipsă | |
| **RDW** | 12,5 % | ❌ Lipsă | |
| **Trombocite** | 267.000 /mm³ | ⚠️ Greșit | Asociere cu valoarea Leucocite (6.440) |
| **Leucocite** | 6.440 /mm³ | ❌ Implicit | Valoarea apare pe linia Trombocite |
| **Neutrofile** | 3.070 /mm³, 47,67% | ✅ 47,67% | Lipsă valoarea absolută |
| **Limfocite** | 2.410 /mm³, 37,43% | ✅ 37,43% | Lipsă valoarea absolută |
| **Monocite** | 440 /mm³, 6,83% | ✅ 6,83% | Lipsă valoarea absolută |
| **Eozinofile** | 480 /mm³, 7,45% | ✅ 7,45% | Lipsă valoarea absolută |
| **Bazofile** | 40 /mm³, 0,62% | ✅ 0,62% | Lipsă valoarea absolută |
| **TGO (ASAT)** | < 8 U/L | ✅ | Valoare text "< 8" |
| **TGP (ALAT)** | 20 U/L | ❌ Lipsă | |
| **Calciu ionic** | 1,35 mmol/L | ✅ 1.35 | |
| **Calciu total** | 10,3 mg/dL | ❌ Lipsă | |
| **eGFR** | 130,02 mL/min/1.73m² | ❌ Lipsă | |
| **Creatinină** | 0,52 mg/dL | ✅ 0.52 | |
| **Magneziu** | 1,92 mg/dL | ✅ 1.92 | |
| **Fosfataza alcalină** | 58,0 U/L | ✅ 58.0 | |
| **Fier seric** | 58 μg/dL | ✅ 58.0 | |
| **Feritină** | 12,4 ng/mL | ✅ 12.4 | |
| **TSH** | 1,690 μUI/mL | ✅ 1.69 | |
| **FT4** | 1,01 ng/dL | ✅ 1.01 | |
| **Vitamina B12** | 496 pg/mL | ✅ 496 | |
| **Glucoză** | 80 mg/dL | ✅ 80 | |
| **PH urină** | 5,5 | ❌ Lipsă | |
| **Densitate urină** | 1,029 | ❌ Lipsă | |
| **Proteine urină** | Negativ | ✅ | |
| **Glucoză urină** | Normal | ✅ | |
| **Nitriți** | Negativ | ⚠️ | Asociere greșită cu Urobilinogen |
| **Leucocite sediment** | 1 /μL | ❌ Lipsă | |
| **Celule epiteliale sediment** | 2 /μL | ❌ Lipsă | |
| **F, 28 ani** | – | ⚠️ Gunoi | Sex/vârstă parsejat greșit |

---

## Rezumat

- **Corecte / ok:** ~18
- **Lipsă:** Hemoglobină, Hematocrit, MCV, MCH, MCHC, RDW, Leucocite (val. absol.), TGP, Calciu total, eGFR, PH, Densitate, sediment
- **Greșit:** Hematii (asociere antet), Trombocite (valoare Leucocite), Nitriți (asociere Urobilinogen)
- **Gunoi:** "F, 28 ani"

---

## Cauze

1. **Antet cu dată:** "Hemoleucogramă 10.02.2025" – parserul asociază antetul cu linia următoare.
2. **Valori antecedente pe aceeași linie:** `4.460.000 ... 3.530.000` – al treilea număr e antecedent, nu interval.
3. **Format 2 linii Bioclinica:** Parametru pe o linie, valoare pe alta – duce la perechi greșite (Trombocite ↔ Leucocite).
4. **Excludere insuficientă:** "F, 28 ani" nu e exclusă ca gunoi.
5. **TGP între blocuri:** Linia TGP este între TGO și Calciu, posibil să fie ratată de parser.
