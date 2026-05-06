import sys, os
sys.path.insert(0, r'd:\Ionut analize')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from backend.parser import _linie_este_exclusa, _parse_oneline
from backend.ocr_corrections import corecteaza_ocr_linie_buletin

tests = [
    '| Hemoglobina Glicozilata . 14,80 % -.',
    '| Aparat: BIO- RAD D 10; Metoda: HPLC,',
    'Hemoglobina Glicozilata 14,80 %',
    '4.Ureeserica . 465mgdd 10-50 mg/dl',
    '4.Ureeserica . 10-50 mg/dl',
    '_5.Glicemie 357 mgdi 60-108 mg/dl',
    '6.Creatinina serica . 074 mgd 0,8-1,3 mg/dl',
    '13.Proteina C reactiva . 15mgl <6mg/l',
    '17. PSA (Antigen Specific Prostatic) 6,39 ngml 0-4 ng/ml',
    'Leucocite (WBC) 5,95 10*9/l 4-10',
    'Neutrofile% 64,9% 45-80%',
    'Trombocite (PLT) 288 10*9/l 150-400',
    'Hemoglobina eritrocitara medie (VCH) . 30,8pg 21-35pg',
    '_11.LDL Cholesterol 160 mg/dl',
    'HDL Colesterol 48 mg/dl',
]

print('=== EXCLUDERI ===')
for t in tests:
    excl = _linie_este_exclusa(t)
    fixed = corecteaza_ocr_linie_buletin(t)
    r = _parse_oneline(fixed) if not excl else None
    excl_str = 'X EXCLUS' if excl else '  OK    '
    parse_str = f'=> {r.denumire_raw!r} = {r.valoare} {r.unitate}' if r else '(neparsat)'
    print(f'{excl_str}  {t!r}')
    if not excl:
        print(f'         {parse_str}')
