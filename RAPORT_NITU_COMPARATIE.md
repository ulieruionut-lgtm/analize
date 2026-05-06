# Raport comparație: Nitu – PDF vs ce este încărcat în DB

## Date din PDF (buletin 13.02.2026, Bioclinica)

| # | Parametru | Valoare | Unitate | În DB? |
|---|-----------|---------|---------|--------|
| 1 | Hematii | 4.650.000 | /mm³ | ⚠️ Greșit (asociere cu "Hemoleucogramă") |
| 2 | Hemoglobină | 13,3 | g/dL | ❌ Lipsă |
| 3 | Hematocrit | 38,1 | % | ❌ Lipsă |
| 4 | MCV | 81,9 | fL | ❌ Lipsă |
| 5 | MCH | 28,6 | pg | ❌ Lipsă |
| 6 | MCHC | 34,9 | g/dL | ❌ Lipsă |
| 7 | RDW | 13,1 | % | ❌ Lipsă |
| 8 | Trombocite | 323.000 | /mm³ | ⚠️ Asociere greșită (valoare Leucocite) |
| 9 | Leucocite | 3.980 | /mm³ | ✅ |
| 10 | Neutrofile | 2.260 /mm³ + 56,78 % | /mm³, % | ✅ (doar %) |
| 11 | Limfocite | 1.150 /mm³ + 28,89 % | /mm³, % | ✅ |
| 12 | Monocite | 460 /mm³ + 11,56 % | /mm³, % | ✅ |
| 13 | Eozinofile | 60 /mm³ + 1,51 % | /mm³, % | ✅ |
| 14 | Bazofile | 50 /mm³ + 1,26 % | /mm³, % | ✅ |
| 15 | Proteina C reactivă | 2,260 | mg/dL | ❌ Lipsă |
| 16 | TGO (ASAT) | 74 | U/L | ❌ Lipsă |
| 17 | TGP (ALAT) | 64 | U/L | ✅ |
| 18 | Creatinină serică | 0,27 | mg/dL | ✅ |

## Ce există în DB (11 înregistrări)

1. Hemoleucogramă → Hematii 4.650.000... (valoare salvată ca text, asociere incorectă)
2. Trombocite... → Leucocite 3.980... (parametru și valoare din linii diferite)
3. TGP (ALAT) → 64 U/L ✅
4. Creatinină serică → 0,27 mg/dL ✅
5. M, → 1 an (GUNOI – din "NITU MATEI M, 1 an")
6. Neutrofile 2.260/mm³ → 56,78 % ✅
7. Limfocite 1.150/mm³ → 28,89 % ✅
8. Monocite 460/mm³ → 11,56 % ✅
9. Eozinofile 60/mm³ → 1,51 % ✅
10. Bazofile 50/mm³ → 1,26 % ✅
11. Răspuns rapid ... → 4.0 (GUNOI – din interpretare CRP)

---

## Cauze principale

### 1. Format Bioclinica: parametru + valoare pe aceeași linie

PDF: `Hematii 4.650.000 /mm³ (3.700.000 - 5.150.000)`

Parserul așteaptă fie:
- format 2 linii: linie 1 = parametru, linie 2 = valoare UM (interval)
- format 1 linie MedLife: parametru + valoare + UM + interval

În Bioclinica, totul e pe o linie: parametru + valoare + UM + interval.

### 2. Numere cu separator de mii (punct)

`4.650.000`, `323.000`, `3.980` folosesc punct ca separator de mii.

Regex-ul actual pentru număr: `\d+[.,]\d+` – acceptă un singur punct/virgulă, nu și mii.

### 3. Antet „Hemoleucogramă”

„Hemoleucogramă” e antet de secțiune; următoarea linie conține parametrul și valoarea.

Parserul face match cu format 2 linii și asociază greșit: antet → valoarea de pe linia următoare.

### 4. Linii care nu sunt analize

- „M, 1 an” (sex, vârstă)
- „Răspuns rapid … < 0,4” (interpretare CRP)

Acestea sunt preluate greșit ca rezultate.

---

## Ce trebuie modificat în parser

1. **Format Bioclinica pe o linie**  
   Să recunoască: `Parametru Valoare UM (min - max)` pe aceeași linie.

2. **Numere cu separator de mii**  
   Să preproceseze `4.650.000` → `4650000` înainte de conversie la `float`.

3. **Excludere antete ca parametri**  
   „Hemoleucogramă”, „Formula leucocitară” etc. să nu fie tratate ca parametri, ci ca antete.

4. **Excludere linii gunoi**  
   Pattern pentru „M, 1 an”, „Răspuns rapid …”, etc., să nu intre ca rezultate.

5. **Parametri cu două valori (nr. + %)**  
   Ex: „Neutrofile 2.260 /mm³ 56,78 %” – să salveze ambele (valoare numerică și procent), nu doar procentul.

---

## Cum poți ajuta sistemul să învețe

1. **Analize necunoscute**  
   După upload, verifică tab-ul „Analize necunoscute” și asociază manual fiecare cu analiza standard corectă. Asocierea se salvează ca alias pentru viitor.

2. **Corectare manuală**  
   Editează rezultatele greșite; pentru unele câmpuri nu există încă mecanism de „învățare” din editare.

3. **Alias-uri**  
   Adaugă în DB alias-uri pentru denumiri alternative (ex: „Hematii” → Hematii, „TGO (ASAT)” → TGO etc.).

4. **Varietate de buletine**  
   Încarcă buletine de la mai multe laboratoare (Bioclinica, MedLife, Regina Maria, Synevo). Fiecare format nou ajută la generalizare.

5. **Feedback**  
   Dacă sistemul face erori repetitive, raportezi formatul și valorile așteptate; parserul poate fi ajustat pentru acel format.
