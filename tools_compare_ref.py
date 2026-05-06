"""Compară extract_rezultate(PDF) cu lista de referință utilizator."""
import re
import unicodedata
from pathlib import Path

from backend.pdf_processor import extract_text_from_pdf
from backend.parser import extract_rezultate

PDF = Path(
    r"c:\Users\Ionut\AppData\Roaming\Cursor\User\workspaceStorage"
    r"\a9286e2cac6d7b0788d913c4d6803a14\pdfs\e93b66ab-da55-4f57-9188-5dfb8b9c8aa6"
    r"\Rezultat_24496450.pdf"
)


def norm(s: str) -> str:
    s = (s or "").lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def close(a, b, eps: float = 0.06) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= eps + 1e-9


# excluderi pentru disambiguare (substring în denumire normată)
EXCLUDE: dict[str, list[str]] = {
    "erit_bio": ["sediment", "epitelial", "foarte"],
    "leu_bio": ["sediment", "foarte", "epitelial"],
    "neut_abs": ["procent", "%"],
    "eos_abs": ["procent", "%"],
    "bas_abs": ["procent", "%"],
    "lym_abs": ["procent", "%"],
    "mon_abs": ["procent", "%"],
    "neut_pct": ["mii", "mil"],
    "eos_pct": ["mii", "mil"],
    "bas_pct": ["mii", "mil"],
    "lym_pct": ["mii", "mil"],
    "mon_pct": ["mii", "mil"],
    "rac": [],  # handled: longest match
}


def pick_row(rs, needles: list[str], exclude: list[str]):
    best = None
    best_len = 9999
    for r in rs:
        d = norm(r.denumire_raw or "")
        if not all(n in d for n in needles):
            continue
        if any(x in d for x in exclude):
            continue
        if len(d) < best_len:
            best_len = len(d)
            best = r
    return best


EXPECTED: dict[str, tuple[float | None, tuple | None, str, list[str], list[str]]] = {
    # key: (val, (imin, imax) sau None, 'n'|'t', needles, exclude_extra)
    "rbc": (5.46, (4.44, 5.61), "n", ["rbc"], []),
    "hgb": (15.7, (13.5, 16.9), "n", ["hgb"], []),
    "hct": (46.3, (40, 49.4), "n", ["hct"], []),
    "mcv": (84.8, (81.8, 95.5), "n", ["mcv"], []),
    "mch": (28.8, (27, 32.3), "n", ["mch"], []),
    "mchc": (33.9, (32.4, 35), "n", ["mchc"], []),
    "rdw": (13.1, (11.6, 14.8), "n", ["rdw"], []),
    "wbc": (7.12, (3.91, 10.9), "n", ["wbc"], []),
    # «%» dispare la norm(); folosim „procentul” + marker din paranteză
    "neut_pct": (66.3, (41, 70.7), "n", ["procentul", "neut"], EXCLUDE["neut_pct"]),
    "eos_pct": (2.2, (0.6, 7.6), "n", ["procentul", "eozin"], EXCLUDE["eos_pct"]),
    "bas_pct": (0.8, (0.1, 1.2), "n", ["procentul", "bazof"], EXCLUDE["bas_pct"]),
    "lym_pct": (21.6, (19.1, 47.9), "n", ["procentul", "limfo"], EXCLUDE["lym_pct"]),
    "mon_pct": (9.1, (5.2, 15.2), "n", ["procentul", "monoc"], EXCLUDE["mon_pct"]),
    "neut_abs": (4.71, (1.8, 6.98), "n", ["neut"], EXCLUDE["neut_abs"]),
    "eos_abs": (0.16, (0.03, 0.59), "n", ["eos"], EXCLUDE["eos_abs"]),
    "bas_abs": (0.06, (0.01, 0.07), "n", ["bas"], EXCLUDE["bas_abs"]),
    "lym_abs": (1.54, (1.26, 3.35), "n", ["lym"], EXCLUDE["lym_abs"]),
    "mon_abs": (0.65, (0.29, 0.95), "n", ["mon"], EXCLUDE["mon_abs"]),
    "plt": (319, (150, 450), "n", ["plt"], []),
    "mpv": (9.9, (7.4, 13), "n", ["mpv"], []),
    "pdw": (11.3, (8, 16.5), "n", ["pdw"], []),
    "acid_uric": (7.29, (3.7, 9.2), "n", ["acid", "uric"], []),
    "alt": (39.57, (10, 49), "n", ["alanin"], []),
    "ast": (27.76, (0, 34), "n", ["aspartat"], []),
    "hdl": (40.7, (60, None), "n", ["hdl"], []),
    # Parser: prag <100 uneori fără interval_max în model
    "ldl": (118, None, "n", ["ldl"], []),
    "creat_ser": (0.86, (0.6, 1.1), "n", ["creatinina", "serica"], []),
    "egfr": (91.4, None, "n", ["egfr"], []),
    "glicemie": (96.35, (60, 99), "n", ["glucoza", "serica"], []),
    "k": (4.48, (3.5, 5.1), "n", ["potasiu"], []),
    "na": (139, (136, 145), "n", ["sodiu"], []),
    "tg": (110, None, "n", ["trigliceride"], []),
    "ph_ur": (6, (5, 7), "n", ["ph", "urinar"], []),
    "dens": (1008, (1010, 1030), "n", ["densitate"], []),
    "bili": (None, None, "t", ["bilirubin"], []),
    "uro": (None, None, "t", ["urobilinogen"], []),
    "glu_ur": (None, None, "t", ["glucoza", "urinar"], []),
    "ceton": (None, None, "t", ["corpi", "ceton"], []),
    "erit_bio": (None, None, "t", ["eritrocit"], EXCLUDE["erit_bio"]),
    "leu_bio": (None, None, "t", ["leucocit"], EXCLUDE["leu_bio"]),
    "nitrit": (None, None, "t", ["nitrit"], []),
    "prot_ur": (None, None, "t", ["proteine", "urinar"], []),
    "ft4": (11.42, (11.5, 22.7), "n", ["ft4"], []),
    "tsh": (8.631, (0.55, 4.78), "n", ["tsh"], []),
    "alb_ur": (0.1, None, "n", ["albumina", "urina spontana"], []),
    "cr_ur": (36.1, (40, 260), "n", ["creatinina", "urina spontana"], []),
    "rac": (0.28, (None, 30), "n", ["raport", "albumina"], []),
}

TEXT_OK = {
    "bili": ("negativ",),
    "uro": ("normal",),
    "glu_ur": ("normal",),
    "ceton": ("absenti", "absent"),
    "erit_bio": ("absente", "absent"),
    "leu_bio": ("negativ",),
    "nitrit": ("absenti", "absent"),
    "prot_ur": ("absente", "absent"),
}


def check_num(r, ev, intr) -> tuple[bool, str]:
    if not close(r.valoare, ev, 0.06):
        return False, f"val {r.valoare} != {ev}"
    if intr is None:
        return True, "ok"
    lo, hi = intr
    if lo is not None and (r.interval_min is None or not close(r.interval_min, lo)):
        return False, f"min {r.interval_min} vs {lo}"
    if hi is not None and (r.interval_max is None or not close(r.interval_max, hi)):
        return False, f"max {r.interval_max} vs {hi}"
    return True, "ok"


def check_txt(r, key: str) -> tuple[bool, str]:
    vt = (r.valoare_text or "").strip().lower()
    for tok in TEXT_OK.get(key, ()):
        if tok in vt:
            return True, vt
    return bool(vt), vt or "(gol)"


def main() -> None:
    if not PDF.exists():
        print("PDF lipsă:", PDF)
        return
    text, _, _, _, _ = extract_text_from_pdf(str(PDF))
    rs = extract_rezultate(text)
    print("Parsate din PDF:", len(rs), "rânduri\n")

    ok_c = diff_c = miss_c = 0
    rows: list[tuple[str, str, str, str]] = []

    for ek, spec in EXPECTED.items():
        ev, intr, typ, needles, excl = spec
        ex = list(EXCLUDE.get(ek, [])) + excl
        r = pick_row(rs, needles, ex)
        if r is None:
            miss_c += 1
            rows.append(("LIPSA", ek, "", ""))
            continue
        if typ == "t":
            ok, msg = check_txt(r, ek)
        else:
            ok, msg = check_num(r, ev, intr)
        if ok:
            ok_c += 1
            rows.append(("OK", ek, (r.denumire_raw or "")[:44], msg))
        else:
            diff_c += 1
            rows.append(("DIFF", ek, (r.denumire_raw or "")[:44], msg))

    for st, ek, dn, msg in sorted(rows, key=lambda x: (x[0] != "OK", x[1])):
        print(f"{st:5} | {ek:12} | {dn:44} | {msg}")

    print()
    print(f"Rezumat: OK={ok_c}  DIFF={diff_c}  LIPSA={miss_c}")

    # sediment + culoare din referință (nu toate în EXPECTED)
    sed_ref = [
        "celule epiteliale plate",
        "leucocite sediment",
        "eritrocite sediment",
        "flora bacteriana",
        "celule epiteliale rotunde",
        "mucus",
        "culoare",
        "claritate",
    ]
    print("\n-- Nu sunt în tabelul de mai sus (referință utilizator) --")
    for label in sed_ref:
        print("   •", label, "→ verificare manuală în UI / îmbunătățiri OCR viitoare")

    used = set()
    for ek, spec in EXPECTED.items():
        needles = spec[3]
        ex = list(EXCLUDE.get(ek, [])) + spec[4]
        r = pick_row(rs, needles, ex)
        if r:
            used.add(id(r))

    extra = [r for r in rs if id(r) not in used]
    print(f"\nRânduri parsate suplimentare (artefacte / dubluri): {len(extra)}")
    for r in extra[:18]:
        print("  +", (r.denumire_raw or "")[:72], "|", r.valoare, "|", (r.valoare_text or "")[:20])


if __name__ == "__main__":
    main()
