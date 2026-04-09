"""
Corecții OCR partajate între normalizer (mapare alias) și parser (chei deduplicare).

Pipeline pe text deja normalizat (lowercase, fără diacritice), folosit de normalizer:
  DIRECT_MAP → REGEX_MAP → DOMAIN_MAP (opțional, după categorie buletin)

Pe linie brută înainte de parsare: `corecteaza_ocr_linie_buletin` (structură, unități, microbiologie).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

# ─── Mapare categorie PDF (RO) → domeniu pentru DOMAIN_MAP ─────────────────


def _normalizeaza_cheie(s: str) -> str:
    """Lowercase + fără diacritice + spații colapsate (fără dependență de normalizer)."""
    if not s:
        return ""
    text = s.strip().lower()
    text = text.replace("ș", "s").replace("ş", "s")
    text = text.replace("ț", "t").replace("ţ", "t")
    text = text.replace("ă", "a").replace("â", "a").replace("î", "i")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip()


def categorie_la_domeniu(categorie: Optional[str]) -> Optional[str]:
    """
    Deduce domeniul pentru corecții suplimentare din secțiunea/categoria extrasă din PDF.
    Returnează chei: microbiology | urine | hematology | biochemistry sau None.
    """
    if not categorie or not str(categorie).strip():
        return None
    cat = _normalizeaza_cheie(str(categorie))
    if not cat:
        return None
    if any(
        x in cat
        for x in (
            "microbio",
            "microorgan",
            "cultur",
            "bacteri",
            "antibiogram",
            "myco",
            "fung",
        )
    ):
        return "microbiology"
    if any(x in cat for x in ("urin", "sediment", "sumar urinar", "urocult", "urogram")):
        return "urine"
    if any(
        x in cat
        for x in (
            "hemato",
            "hemoleuco",
            "hemogram",
            "hematolog",
            "sange oscilogra",
            "sange oscilograf",
            "coagul",
        )
    ):
        return "hematology"
    if any(
        x in cat
        for x in (
            "biochim",
            "metabol",
            "electrolit",
            "hepat",
            "renal",
            "lipid",
            "glucid",
        )
    ):
        return "biochemistry"
    return None


# ─── 1. Mapări deterministe (chei deja normalizate: lowercase, fără diacritice) ─
# Înlocuire substring, ordine: cele mai lungi primele (evită înlocuiri parțiale greșite).

_DIRECT_PAIRS: Tuple[Tuple[str, str], ...] = (
    # Microbiologie (frecvent OCR)
    ("staphvlococcus aureus", "staphylococcus aureus"),
    ("staphilococcus aureus", "staphylococcus aureus"),
    ("ha_emophi_lus influenzae", "haemophilus influenzae"),
    ("haemophilus influenzac", "haemophilus influenzae"),
    ("moraxella catarrhalis-", "moraxella catarrhalis"),
    ("enterobacteriaceae -", "enterobacteriaceae"),
    ("clostridiumdifficile", "clostridium difficile"),
    ("toxina clostridium difficile", "clostridium difficile toxina"),
    ("candida spp", "candida spp."),
    # Hematologie / urină (OCR RO)
    ("pla chetar", "plachetar"),
    ("pla.chetar", "plachetar"),
    ("eritrocitare", "eritrocite"),
    ("leucocite foarte", "leucocite"),
    ("tranzmonale", "tranzitionale"),
    ("tranzutlonale", "tranzitionale"),
    ("epitellal", "epiteliale"),
    ("celule epitellale", "celule epiteliale"),
    ("celule epiteliale tranzmonale", "celule epiteliale tranzitionale"),
    ("aciduric", "acid uric"),
    ("negativ.", "negativ"),
    ("normal.", "normal"),
)

_DIRECT_MAP_SORTED: List[Tuple[str, str]] = sorted(
    _DIRECT_PAIRS, key=lambda p: len(p[0]), reverse=True
)

# ─── 2. Regex pe text normalizat (păstrăm setul existent + completări sigure) ─

REGEX_MAP_NORMALIZAT: Tuple[Tuple[str, str], ...] = (
    (r"\bumar\b", "numar"),
    (r"\bcrealinin[ae]?\b", "creatinina"),
    (r"\bglu[o0]{2,}za\b", "glucoza"),
    (r"\bhemoglo[b6]ina\b", "hemoglobina"),
    (r"\bh[ce]moglobina\b", "hemoglobina"),
    (r"\bhemat[o0]crit\b", "hematocrit"),
    (r"\bleuc[o0]cite\b", "leucocite"),
    (r"\btr[o0]mbocite\b", "trombocite"),
    (r"\bferit[i1]na\b", "feritina"),
    (r"\bcolester[o0]l\b", "colesterol"),
    (r"\btriglicer[i1]de\b", "trigliceride"),
    (r"\berit[ro]cite\b", "eritrocite"),
    (r"pla\.?\s*chetar", "plachetar"),
    (r"tranzmonale", "tranzitionale"),
    (r"tranzutlonale", "tranzitionale"),
    (r"\bha[_\s]*emophi[_\s!l1i]*us\b", "haemophilus"),
    (r"\bhaemophilus\s+influenz\w*\b", "haemophilus influenzae"),
    (r"^\s*eriaceae\b", "enterobacteriaceae"),
    (r"\s+eriaceae\b", " enterobacteriaceae"),
    (r"\bentero\s*bacteriaceae\b", "enterobacteriaceae"),
    (r"\bmoraxel{1,3}a\b", "moraxella"),
    (r"\bstaphylo[_\s]*coc\w*\s+aureus\b", "staphylococcus aureus"),
    (r"\bclostridi\w*\s+difficile\b", "clostridium difficile"),
    (r"\bdiagnostipz\b", "diagnostic"),
    (r"\bdiagn[o0]stipz\b", "diagnostic"),
    # Completări sigure (fără staph\w+ / eritro\w+ prea largi)
    (r"(\d)\s*\.\s*(\d)", r"\1.\2"),
    (r"mg\s*/\s*d[il1]\b", "mg/dl"),
    (r"iplate", "plate"),
    (r"\btgp\b", "alt"),
    (r"\btgo\b", "ast"),
)

# Alias istoric pentru importuri existente
OCR_FIX_PATTERNS_NORMALIZAT: Tuple[Tuple[str, str], ...] = REGEX_MAP_NORMALIZAT

# ─── 3. Corecții pe domeniu (chei normalizate) ───────────────────────────────

DOMAIN_MAP_NORMALIZAT: Dict[str, Dict[str, str]] = {
    "microbiology": {
        "influenzae-": "influenzae",
        "aureus -": "aureus",
        "aureus-": "aureus",
        "spp -": "spp.",
        "spp-": "spp.",
    },
    "urine": {
        "celule epiteliale tranzmonale": "celule epiteliale tranzitionale",
        "celule epiteliale tranzutlonale": "celule epiteliale tranzitionale",
    },
}

# Regex suplimentare per domeniu (RBC/WBC; glucoza → glicemie doar în biochimie)
_DOMAIN_REGEX: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "hematology": (
        (r"\brbc\b", "eritrocite"),
        (r"\bwbc\b", "leucocite"),
    ),
    "biochemistry": (
        (r"\bglucoza\b", "glicemie"),
    ),
}


def aplica_pipeline_ocr_normalizat(
    raw_norm: str, domain: Optional[str] = None, *, log_changes: bool = False
) -> str:
    """
    Ordine: DIRECT_MAP → REGEX → regex domeniu → DOMAIN substring.

    `raw_norm` trebuie deja trecut prin aceeași normalizare ca `normalizer._normalizeaza`.
    """
    if not raw_norm or not raw_norm.strip():
        return raw_norm
    original = raw_norm
    text = raw_norm

    for wrong, right in _DIRECT_MAP_SORTED:
        if wrong in text:
            text = text.replace(wrong, right)

    for pattern, repl in REGEX_MAP_NORMALIZAT:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    if domain:
        for pattern, repl in _DOMAIN_REGEX.get(domain, ()):
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        dm = DOMAIN_MAP_NORMALIZAT.get(domain)
        if dm:
            for wrong, right in sorted(dm.items(), key=lambda x: len(x[0]), reverse=True):
                if wrong in text:
                    text = text.replace(wrong, right)

    text = re.sub(r"\s+", " ", text).strip()
    if log_changes and text != original:
        _log.debug("[OCR_PIPELINE] %r -> %r (domain=%s)", original, text, domain)
    return text


def aplică_corectii_ocr_normalizat(raw_norm: str) -> str:
    """Compatibilitate: pipeline fără domeniu (doar DIRECT + REGEX)."""
    return aplica_pipeline_ocr_normalizat(raw_norm, domain=None)


def text_ocr_suspect(s: str) -> bool:
    """Heuristic scurt: posibil fragment OCR incomplet (pentru triaj / debug)."""
    if not s or not str(s).strip():
        return True
    t = str(s).strip()
    if len(t) < 4:
        return True
    if re.match(r"^\d", t) and len(t) < 8:
        return True
    return False


def corecteaza_ocr_linie_buletin(linie: str) -> str:
    """
    Corecții OCR pe linie înainte de parsare.
    Nu înlocuiește agresiv — doar pattern-uri frecvente din buletine reale.
    """
    if not linie or not linie.strip():
        return linie
    s = linie

    # --- Prefix | la inceput de linie (Sante Vie: "| Hemoglobina Glicozilata 14,80 %") ---
    s = re.sub(r"^\|\s*", "", s)

    # --- Prefix numeric N. sau _N. inainte de denumire (Sante Vie: "3.Acid uric", "_5.Glicemie") ---
    # NU stergem daca dupa "N." urmeaza cifra (ex: "2.236 uUI/mL" = valoare reala, nu prefix sectiune)
    s = re.sub(r"^_?\d{1,2}\.\s*(?=[A-Za-zĂÂÎȘȚăâîșț#_])", "", s)
    # Prefix cifra + litere mici la incepul denumirii, inainte de separarea generala
    # (Sante Vie: "4dUreeserica" -> "Ureeserica"; trebuie sa fie inainte de regula de separare
    #  care ar da "4d" -> "4 d" si ar strica pattern-ul)
    s = re.sub(r"^\d+[a-zA-Z]{1,4}([A-ZĂÂÎȘȚ])", r"\1", s)

    # --- Simboluri parazite între denumire și valoare (MedLife / Sante Vie scanat) ---
    # 'Hemoglobina Glicozilata . """-—14,80 %' → 'Hemoglobina Glicozilata . 14,80 %'
    s = re.sub(r'["\u201c\u201d\u201e]{2,}[-\u2013\u2014]+(?=\s*\d)', "", s)
    s = re.sub(r'[-\u2013\u2014]{2,}(?=\s*\d)', "", s)
    # "TSH ¢ 2.88" → "TSH 2.88"  |  "TSH * 2.88" → "TSH 2.88"
    # Simboluri: ¢ § ° ~ ` ^ ± ∓ † ‡ ¶ și combinații cu spații
    s = re.sub(r"(?<=\s)[¢§°~`^±†‡¶]+(?=\s)", "", s)
    # "TSH¢2.88" (fără spații) → "TSH 2.88"
    s = re.sub(r"([A-Za-z])[¢§°~`^±†‡¶]+(\d)", r"\1 \2", s)

    # --- Unități OCR corupte (MedLife, Synevo scanat) ---
    # pmoliL / pmolil / pmoll → pmol/L  (cu sau fara spatiu inaintea unitatii)
    s = re.sub(r"\bpmoli?[lL]\b", "pmol/L", s)
    s = re.sub(r"(\d)pmoli?[lL]?\b", r"\1 pmol/L", s)  # "230pmoli" → "230 pmol/L"
    # uUl/mt / uUI/mt / uUl/mL → uUI/mL (TSH)
    s = re.sub(r"\bu[Uu][Ii]?/m[tTlL]\b", "uUI/mL", s, flags=re.IGNORECASE)
    # mUl/ml / mUI/ml → mUI/mL
    s = re.sub(r"\bm[Uu][Ii]?/m[lL]\b", "mUI/mL", s, flags=re.IGNORECASE)
    # *10%6 / *10'6 / *106 → *10^6  (eritrocite MedLife)
    s = re.sub(r"\*10[%\'`]6", "*10^6", s)
    # *10'3 / *10%3 / *103 → *10^3
    s = re.sub(r"\*10[%\'`]3", "*10^3", s)
    # *1073 / *1075 / *1073 (OCR confundă ^ cu 7) → *10^3
    s = re.sub(r"\*107([3-6])", r"*10^\1", s)
    # ng/mL scris ca ng/ml (normalizare minora)
    # pUlimL / pUliml → pUI/mL (TSH interval)
    s = re.sub(r"\bp[Uu]l?i?m[lL]\b", "pUI/mL", s)

    # mg/di → mg/dL (OCR confundă L cu i)
    s = re.sub(r"\bmg/di\b", "mg/dL", s, flags=re.IGNORECASE)
    # mgdi / mgdd / mgdl (fara bara) → mg/dL (Sante Vie scanat: "357 mgdi")
    s = re.sub(r"\bmgd[il]\b", "mg/dL", s, flags=re.IGNORECASE)
    s = re.sub(r"\bmgdd\b", "mg/dL", s, flags=re.IGNORECASE)
    # mgl/di / mgl/dl → mg/dL
    s = re.sub(r"\bmgl?/d[il]\b", "mg/dL", s, flags=re.IGNORECASE)
    # 15mgl → 15 mg/L (valoare lipita de unitate, ex CRP)
    s = re.sub(r"(\d)(mgl)\b", r"\1 mg/L", s, flags=re.IGNORECASE)
    # ngml → ng/mL (PSA)
    s = re.sub(r"\bngml\b", "ng/mL", s, flags=re.IGNORECASE)
    # Cifra lipita de % (fara spatiu): 470% → 470 %
    # (\b nu prinde % deoarece % e non-word char, deci regula generala urmatoare il ratează)
    s = re.sub(r"(\d)%(?=[\s,;|]|$)", r"\1 %", s)
    # Valoare lipita de unitate: "30,8pg" → "30,8 pg", "18Bgdl" → "18,8 g/dL"
    s = re.sub(
        r"(\d)([a-zA-ZµμfL%][a-zA-Z/\^0-9µμ]*)\b",
        lambda m: m.group(1) + " " + m.group(2) if not m.group(2).startswith(("e", "E")) else m.group(0),
        s,
    )
    # gdl / gal / g/al → g/dL
    s = re.sub(r"\bg/al\b", "g/dL", s, flags=re.IGNORECASE)
    s = re.sub(r"\bgdl\b", "g/dL", s, flags=re.IGNORECASE)
    # 10*9/l / 10*12/l → 10^9/L / 10^12/L (hematologie Sante Vie)
    s = re.sub(r"\b10\*(\d+)/[lL1]\b", r"10^\1/L", s)
    # 10^9/1 (cifra 1 in loc de L)
    s = re.sub(r"\b10\^(\d+)/1\b", r"10^\1/L", s)
    # 1099/1 / 1099/l → 10^9/L (OCR confundă ^ cu 9)
    s = re.sub(r"\b109(\d)/[1lL]\b", r"10^\1/L", s, flags=re.IGNORECASE)
    # 109 / 1012 ca unitate stand-alone (Sante Vie: "288 109 150-400 10*9/l" → "288 10^9/L 150-400")
    # Numar urmat de " 109 " sau " 1012 " unde 109/1012 e unitate
    s = re.sub(r"\b(\d+[,.]?\d*)\s+109\b(?!\s*[,/\^])", r"\1 10^9/L", s)
    s = re.sub(r"\b(\d+[,.]?\d*)\s+1012\b(?!\s*[,/\^])", r"\1 10^12/L", s)
    # mgd (fara bara) → mg/dL (Sante Vie: "074 mgd")
    s = re.sub(r"\bmgd\b", "mg/dL", s, flags=re.IGNORECASE)
    # IU/ml → UI/mL (normalizare)
    # UL → U/L (Tesseract pierde bara oblică)
    s = re.sub(r"(?<=\d)\s+UL\b", " U/L", s)
    s = re.sub(r"\bUL\b(?=\s*<)", "U/L", s)
    # milmin / mimin → mL/min (GFR Sante Vie)
    s = re.sub(r"\bmilmin\b", "mL/min", s, flags=re.IGNORECASE)
    s = re.sub(r"\bmimin\b", "mL/min", s, flags=re.IGNORECASE)
    # mgg → mg/g (albumina creatinina)
    s = re.sub(r"\bmgg\b", "mg/g", s, flags=re.IGNORECASE)
    # gd (fara bara) → g/dL  ex: "168gd" → "168 g/dL"
    s = re.sub(r"\bgd\b(?!/)", "g/dL", s, flags=re.IGNORECASE)

    # --- Simboluri parazite specifice SANTE VIE scanat ---
    # £ inainte de cifra (OCR confunda espace sau semn egal cu £): £168 → 168
    s = re.sub(r"£(\d)", r"\1", s)
    # « simbol parazit (singur sau urmat de =, spatiu): «= sau « → spatiu
    s = re.sub(r"«+\s*=?\s*", " ", s)
    # $$ la inceput de valoare/linie: $$162% → 162%
    s = re.sub(r"\$\$+", "", s)
    # © ca separator intre valoare si interval (Sante Vie: "168 g/dL © 12,6-17,4")
    # Transformam in spatiu ca sa nu blocheze parsarea intervalului
    s = re.sub(r"\s*©\s*", " ", s)
    # " „ " " (ghilimele ASCII si tipografice) la incepul liniei -> remove
    s = re.sub(r'^[""\u201e\u201c\u201d]+', "", s)
    # mgdi / mgdl dupa separarea generala (cand nu s-a prins inainte: "465 mgdi" -> "465 mg/dL")
    s = re.sub(r"\bmgdi\b", "mg/dL", s, flags=re.IGNORECASE)
    # # simbol parasit inainte de valoare numerica (Sante Vie: "# 470 %")
    s = re.sub(r"\s*#\s*(?=\d)", " ", s)
    # f singur ca unitate (OCR rata "fl"): " f " sau " f\n" (dupa separare) -> " fl "
    s = re.sub(r"\s+f\s+(?=[a-z])", " fl ", s)  # "857 f fl" -> "857 fl fl" -> redundant dar ok
    s = re.sub(r"\bf\b(?=\s|$)", "fl", s)
    # Valoare numerica lipita de f (OCR: fl citit ca f): 857f → 857 fl
    # Evitam sa stricam "g/dL" sau alte unitati cu litere
    s = re.sub(r"(\d)f\b(?![a-zA-Z/])", r"\1 fl", s)

    # --- Artefact OCR MedLife PDR: coloana-separator '|' citit ca litera 'i' la sfarsit de linie ---
    # ex: 'Nr. neutrofile „8.02 *1043/pl i' → 'Nr. neutrofile „8.02 *1043/pl'
    # Sterge NUMAI cand linia se termina cu spatiu + o singura litera mica ('i' sau 'l')
    # dupa o cifra sau o unitate (nu stergem daca ultimul token e o unitate valida multi-char)
    s = re.sub(r"(?<=[\d/lL])\s+[il]\s*$", "", s)

    # --- Microbiologie: organisme corupte ---
    s = re.sub(
        r"Ha[_\s]+emophi[_\s!l1Ii\*]*us",
        "Haemophilus",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"(?<![A-Za-zĂÂÎȘȚăâîșț])eriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    s = re.sub(r"\bEntero\s*bacteriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    s = re.sub(r"\bMoraxel{1,3}a\b", "Moraxella", s, flags=re.IGNORECASE)
    s = re.sub(
        r"\bStaphylo[_\s]*coc\w*\s+aureus\b",
        "Staphylococcus aureus",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bClostridi\w*\s+difficile\b",
        "Clostridium difficile",
        s,
        flags=re.IGNORECASE,
    )
    return s


def corecteaza_umar_numar_in_denumire(s: str) -> str:
    """
    Înlocuiește «umar de» → «numar de» pentru deduplicare / chei (lowercase).
    Folosit de parser la _key_denumire.
    """
    if not s:
        return s
    return re.sub(r"\bumar\s+de\b", "numar de", s, flags=re.IGNORECASE)


def corecteaza_umar_numar_artefact_capitalizat(text: str) -> str:
    """
    Varianta pentru denumiri afișate: «Umar de» → «Numar de» (ca în laborator).
    Folosit de normalizer._curata_artefacte.
    """
    if not text:
        return text
    return re.sub(r"\bumar\s+de\b", "Numar de", text, flags=re.IGNORECASE)
