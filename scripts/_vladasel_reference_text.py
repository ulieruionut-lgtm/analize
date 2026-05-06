# -*- coding: utf-8 -*-
"""Text sintetic din referința utilizatorului (structură tip buletin cu tab-uri) — PDF-ul real e scanat."""
T = chr(9)
# Aproximare rânduri tabel ca în laborator / copy-paste
TEXT = f"""1. Bacteriologie – Exudat faringian
Examen bacteriologic, micologic
Staphylococcus aureus: absent
Streptococ betahemolitic: absent
Candida spp: absent

2. Bacteriologie – Urocultură
Urocultura
Rezultat cantitativ: Bacteriurie <1000 UFC/ml (fără semnificație clinică; pragul de detecție = 1000 UFC/ml)
Organisme absente: Enterococcus spp, Streptococcus spp, Staphylococcus spp, Enterobacteriaceae, Pseudomonas spp, Candida spp

3. Biochimie serică
Test{T}Rezultat{T}Unitate{T}Interval de referință
Factor reumatoid (FR cantitativ){T}<20{T}IU/mL{T}<30
Glicemie (glucoză serică){T}92{T}mg/dL{T}83 – 110
TGO / AST (aspartataminotransferază){T}25{T}U/L{T}11 – 34
TGP / ALT (alaninaminotransferază){T}16{T}U/L{T}0 – 34

4. Examen complet de urină – Sediment urinar (microscopie)
Subanaliză{T}Rezultat
Celule epiteliale plate{T}negativ
Celule epiteliale tranzitionale{T}negativ
Leucocite{T}foarte rare
Hematii{T}negativ
Cilindrii hialini{T}negativ
Cilindri patologici{T}negativ
Cristale de oxalat de calciu{T}negativ
Cristale acid uric{T}negativ
Cristale fosfat amoniaco-magnezian{T}negativ
Cristale amorfe{T}negativ
Alte cristale{T}negativ
Flora microbiană{T}negativă
Levuri{T}negativ
Mucus{T}negativ

5. Hematologie – Hemoleucogramă completă
Test{T}Rezultat{T}Unitate{T}Interval de referință
RDW% (lărgimea distribuției eritrocitare){T}14,7{T}%{T}11,6 – 14,8
WBC (număr leucocite){T}5,81{T}10³/μL{T}4 – 10
Neutrofile %{T}56,3{T}%{T}45 – 80
Limfocite %{T}34,9{T}%{T}20 – 55
Monocite %{T}7,6{T}%{T}0 – 15
Eozinofile %{T}0,7{T}%{T}0 – 7
Bazofile %{T}0,5{T}%{T}0 – 2
Număr neutrofile{T}3,27{T}10³/μL{T}2 – 8
Număr limfocite{T}2,03{T}10³/μL{T}1 – 4
Număr monocite{T}0,44{T}10³/μL{T}0 – 1
Număr eozinofile{T}0,04{T}10³/μL{T}0 – 0,7
Număr bazofile{T}0,03{T}10³/μL{T}0 – 0,2
PLT (număr trombocite){T}191{T}10³/μL{T}150 – 400
MPV (volum trombocitar mediu){T}9,7{T}fL{T}7,4 – 13

6. VSH (Viteză de sedimentare a hematiilor)
VSH (metoda Westergreen): 20 mm/h (referință: <30 mm/h)

7. Hormoni tiroidieni
Test{T}Rezultat{T}Unitate{T}Interval de referință
TSH{T}4,42{T}ulU/mL{T}0,27 – 4,2
FT4 (tiroxină liberă){T}1,23{T}ng/dL{T}0,92 – 1,68
"""


def main() -> None:
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    from backend.parser import parse_full_text
    from backend.lab_detect import resolve_laborator_id_for_text
    from backend.normalizer import normalize_rezultate

    parsed = parse_full_text(TEXT, cnp_optional=True)
    if not parsed:
        print("parse None")
        return
    lab_id, _ = resolve_laborator_id_for_text(TEXT, "vladasel_synthetic.txt")
    normalize_rezultate(parsed.rezultate, laborator_id=lab_id)
    print("rezultate:", len(parsed.rezultate))
    for i, r in enumerate(parsed.rezultate, 1):
        cat = (getattr(r, "categorie", None) or "")[:20]
        vt = (r.valoare_text or "")[:60]
        print(f"{i:3}. [{cat:<20}] {r.denumire_raw!r} v={r.valoare!r} u={r.unitate!r} vt={vt!r}")


if __name__ == "__main__":
    main()
