import re, sys
sys.stdout.reconfigure(encoding="utf-8")

src = open("backend/parser.py", encoding="utf-8").read()
# Inlocuieste importul problematic cu un stub
src = src.replace("from backend.models import PatientParsed, RezultatParsat", "")

class RezultatParsat:
    def __init__(self, **kw): self.__dict__.update(kw)
    def __repr__(self): return f"Rez(raw={self.denumire_raw!r}, val={getattr(self,'valoare',None)}, um={getattr(self,'unitate',None)}, txt={getattr(self,'valoare_text',None)})"

class PatientParsed:
    def __init__(self, **kw): self.__dict__.update(kw)

ns = {"Optional": type(None), "RezultatParsat": RezultatParsat, "PatientParsed": PatientParsed, "re": re}
exec(src, ns)

_este_gunoi_ocr = ns["_este_gunoi_ocr"]
_parse_oneline = ns["_parse_oneline"]
_LINII_EXCLUSE = ns["_LINII_EXCLUSE"]
_este_linie_parametru = ns["_este_linie_parametru"]

print("=== GUNOI OCR (trebuie True) ===")
for t in [
    "Cca aa aaa E O SI A RA e Spezia",
    "i CR CE SERE De E Oa nea Cai ca ei a a ea Mac Saci",
    "Fo e BE II SE PN SR pe POS De Aaaa eee A i at E DE E ae E",
    "pa creme cate ate sa e at e REED aa RI RR A",
    "Laza Ana Ramona A",
    "\u201eST Sie ie e",
]:
    print(f"  {'GUNOI' if _este_gunoi_ocr(t) else 'OK   '}: {t[:60]!r}")

print("\n=== LINII OK (trebuie PASTRAT) ===")
for t in [
    "GLUCOZA SERICA (GLICEMIE)",
    "Numar de eritrocite (RBC)",
    "ALANINAMINOTRANSFERAZA (ALT/GPT/TGP)",
    "Volumul mediu eritrocitar (MCV)",
    "CALCIU SERIC [10.66 mg/dL]",
    "FIER SERIC (SIDEREMIE) [197.52 ug/dL]",
]:
    print(f"  {'PASTRAT' if _este_linie_parametru(t) else 'EXCLUS '}: {t!r}")

print("\n=== PARSE ONELINE ===")
for t in [
    "CALCIU SERIC [10.66 mg/dL]",
    "FIER SERIC (SIDEREMIE) [197.52 ug/dL]",
    "HDL COLESTEROL 68.2 mg/dL > 60 enma V",
    "TRIGLICERIDE 112 mg/dL <150 ME)",
    "FOLATI SERICI (ACID FOLIC) * 7.64 ng/mL >5.38 De A",
    "eGFR: 2",
    "crescute 2 126 mg/dl",
]:
    r = _parse_oneline(t)
    print(f"  {str(r)[:80] if r else 'NICIO VALOARE'}: {t!r}")
