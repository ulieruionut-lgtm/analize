"""
Normalizare denumiri analize: mapare alias → analiza_standard.

Strategii de matching (in ordine, se opreste la primul match):
  1. Exact match (case-insensitive, trimmed)
  2. Exact match dupa curatare artefacte (*, <, >, #)
  3. Match normalizat (diacritice eliminate)
  4. Match fara paranteze + normalizat
  5. Match dupa primele 2 cuvinte semnificative (conservator)
  6. Match dupa >= 3 cuvinte cheie comune
  7. Fuzzy match (similaritate >= 88%) pentru erori OCR (ex: Hcmoglobina -> Hemoglobina)

Daca nu gaseste nimic: salveaza in analiza_necunoscuta pentru aprobare manuala.
"""
import difflib
import logging
import re
import time
import unicodedata
from typing import Optional

from backend.models import RezultatParsat


# ─── Normalizare text ─────────────────────────────────────────────────────────

def _curata_artefacte(text: str) -> str:
    """Elimina artefacte de laborator si OCR: asteriscuri, <, >, #, blocuri [...], etc."""
    # Sterge asteriscuri, semne <> la inceput/sfarsit, artefacte comune OCR
    text = re.sub(r'[\*\<\>\#\~\^]+', ' ', text)
    # Sterge blocuri [valoare unitate] - OCR garbage (ex: "[197.52 wo/a]" lipit de denumire)
    text = re.sub(r'\s*\[\d+[.,]?\d*\s*[\w/]+\]\s*', ' ', text)
    # Sterge trailing " :" sau ":" (artefact OCR de la sfarsitul denumirii)
    text = re.sub(r'\s*:\s*$', '', text)
    # Corectare OCR frecventa: "umar" -> "Numar" (N citit gresit ca u)
    text = re.sub(r'\bumar\s+de\b', 'Numar de', text, flags=re.IGNORECASE)
    # Sterge spatii multiple si trimeaza
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _normalizeaza(text: str) -> str:
    """Lowercase + eliminare diacritice + collapse whitespace."""
    text = text.strip().lower()
    # Elimina diacritice romanesti si internationale
    text = text.replace('ș', 's').replace('ş', 's')
    text = text.replace('ț', 't').replace('ţ', 't')
    text = text.replace('ă', 'a').replace('â', 'a').replace('î', 'i')
    # Elimina restul diacriticelor prin unicode decompose
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    # Colapseaza spatii multiple
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _fara_paranteze(text: str) -> str:
    """Elimina tot ce e intre paranteze: 'TGO (ASAT)' → 'TGO'."""
    return re.sub(r'\s*\(.*?\)', '', text).strip()


def _cuvinte_cheie(text: str) -> set:
    """Extrage cuvinte cu >= 3 litere (ignora unitati, cifre)."""
    return {w for w in re.split(r'[\s\-/\(\)]+', text) if len(w) >= 3 and not w.isdigit()}


def _strip_prefix_regina_maria(raw: str) -> str:
    """
    Elimina prefixele numerice din formatul Regina Maria (Nr. denumire test).
    Ex: "1.1.4 Glucoza Negativ mg/dL" -> "Glucoza Negativ mg/dL"
        "1.2.4" -> "" (doar nr, nu e parametru)
        "1:2 HGB (Hemoglobina) 13.2" -> "HGB (Hemoglobina) 13.2"
        "1-3 HCT% (Hematocrit)" -> "HCT% (Hematocrit)"
    """
    s = raw.strip()
    # Pattern: inceput cu cifre, punct/virgula/doua puncte/liniuta, eventual mai multe grupuri
    # ex: 1.1.4, 1.2.4, 1:2, 1-3, 4:18, 11,13, $.1.11, 1,2:5, ai: RDW%
    m = re.match(r'^((?:ai\s*:\s*)?\$?[\d\.\,\:\-]+\s*\*?\s*)', s, re.IGNORECASE)
    if m:
        rest = s[m.end():].strip()
        if len(rest) >= 2:  # ramane ceva util
            return rest
    return s


# Cache in-memory cu TTL de 3 minute - se reincarc automat din DB
# Astfel aliasurile adaugate direct in DB sunt preluate rapid, fara restart
_CACHE: Optional[dict] = None
_CACHE_RAW: Optional[dict] = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECUNDE: int = 60  # 1 minut - invata rapid alias-urile aprobate (inclusiv cu multi-worker)


def _incarca_cache() -> tuple[dict, dict]:
    global _CACHE, _CACHE_RAW, _CACHE_TIMESTAMP
    acum = time.time()
    # Reincarc daca cache-ul este gol SAU a expirat (TTL)
    if _CACHE is not None and (acum - _CACHE_TIMESTAMP) < _CACHE_TTL_SECUNDE:
        return _CACHE, _CACHE_RAW
    try:
        from backend.database import get_cursor, _use_sqlite
        cache_norm = {}
        cache_raw = {}
        with get_cursor(commit=False) as cur:
            cur.execute("SELECT alias, analiza_standard_id FROM analiza_alias")
            for row in cur.fetchall():
                if row is None:
                    continue
                try:
                    alias_val = row['alias'] if hasattr(row, 'keys') else row[0]
                    aid_val = row['analiza_standard_id'] if hasattr(row, 'keys') else row[1]
                    alias = str(alias_val)
                    aid = int(aid_val)
                    cache_raw[alias.lower()] = aid
                    cache_norm[_normalizeaza(alias)] = aid
                except (IndexError, KeyError, TypeError):
                    continue
        _CACHE = cache_norm
        _CACHE_RAW = cache_raw
        _CACHE_TIMESTAMP = acum
        return _CACHE, _CACHE_RAW
    except Exception:
        return {}, {}


def invalideaza_cache():
    """Apelat dupa ce se adauga un alias nou - forteaza reincarcare imediata."""
    global _CACHE, _CACHE_RAW, _CACHE_TIMESTAMP
    _CACHE = None
    _CACHE_RAW = None
    _CACHE_TIMESTAMP = 0.0


def _cauta_in_cache(raw: str) -> Optional[int]:
    """
    Incearca mai multe strategii de matching si returneaza analiza_standard_id sau None.
    Daca nu gaseste nimic sigur, returneaza None (va fi salvata ca necunoscuta).
    """
    cache_norm, cache_raw = _incarca_cache()
    if not cache_norm:
        return None

    raw = raw.strip()
    # Elimina prefixe Regina Maria (1.1.4, 1:2, 1-3, ai:, $.1.11) inainte de matching
    raw = _strip_prefix_regina_maria(raw)
    # Curata artefactele de laborator (*, <, >, etc.) inainte de matching
    raw_curat = _curata_artefacte(raw)
    raw_lower = raw_curat.lower()
    raw_norm = _normalizeaza(raw_curat)
    raw_fara_par = _normalizeaza(_fara_paranteze(raw_curat))

    # 1. Exact match pe textul original (case-insensitive)
    if raw.lower() in cache_raw:
        return cache_raw[raw.lower()]

    # 2. Exact match dupa curatare artefacte (case-insensitive)
    if raw_lower in cache_raw:
        return cache_raw[raw_lower]

    # 3. Match normalizat (diacritice eliminate)
    if raw_norm in cache_norm:
        return cache_norm[raw_norm]

    # 4. Match fara paranteze + normalizat
    if raw_fara_par and raw_fara_par in cache_norm:
        return cache_norm[raw_fara_par]

    # 4b. Corectii OCR frecvente pentru termeni medicali români (eroare -> corect)
    _OCR_FIXES = (
        (r'\bumar\b', 'numar'),              # N citit gresit ca u
        (r'\bcrealinin[ae]?\b', 'creatinina'),
        (r'\bglu[o0]{2,}za\b', 'glucoza'),   # gluooza, glu0za
        (r'\bhemoglo[b6]ina\b', 'hemoglobina'),
        (r'\bh[ce]moglobina\b', 'hemoglobina'),  # hcmoglobina
        (r'\bhemat[o0]crit\b', 'hematocrit'),
        (r'\bleuc[o0]cite\b', 'leucocite'),
        (r'\btr[o0]mbocite\b', 'trombocite'),
        (r'\bferit[i1]na\b', 'feritina'),
        (r'\bcolester[o0]l\b', 'colesterol'),
        (r'\btriglicer[i1]de\b', 'trigliceride'),
        (r'\berit[ro]cite\b', 'eritrocite'),
    )
    raw_ocr_fix = raw_norm
    for pattern, repl in _OCR_FIXES:
        raw_ocr_fix = re.sub(pattern, repl, raw_ocr_fix, flags=re.IGNORECASE)
    if raw_ocr_fix != raw_norm and raw_ocr_fix in cache_norm:
        return cache_norm[raw_ocr_fix]

    # 5. Match dupa primele 2 cuvinte semnificative (mai conservator)
    cuvinte = [w for w in re.split(r'[\s\-/\(\)]+', raw_norm) if len(w) >= 3 and not w.isdigit()]
    if len(cuvinte) >= 2:
        first_two = cuvinte[:2]
        for alias_norm, aid in cache_norm.items():
            alias_cuvinte = [w for w in re.split(r'[\s\-/\(\)]+', alias_norm)
                             if len(w) >= 3 and not w.isdigit()]
            if len(alias_cuvinte) >= 2 and alias_cuvinte[:2] == first_two:
                return aid

    # 6. Match dupa cuvinte cheie comune (>= 3 cuvinte comune, evita false pozitive)
    raw_kw = _cuvinte_cheie(raw_norm)
    if len(raw_kw) >= 3:
        for alias_norm, aid in cache_norm.items():
            alias_kw = _cuvinte_cheie(alias_norm)
            if len(raw_kw & alias_kw) >= 3:
                return aid

    # 7. Fuzzy matching pentru erori OCR (ex: "Hcmoglobina" -> "Hemoglobina")
    # Folosim difflib.get_close_matches cu threshold 0.88 - suficient de strict
    # pentru a evita false pozitive dar prinde erorile tipice OCR (1-2 litere gresite)
    if len(raw_norm) >= 5:  # nu aplica pe denumiri prea scurte
        matches = difflib.get_close_matches(raw_norm, cache_norm.keys(), n=1, cutoff=0.88)
        if matches:
            return cache_norm[matches[0]]

    return None


def _log_necunoscuta(denumire_raw: str) -> None:
    """Salveaza analiza necunoscuta in DB pentru aprobare ulterioara."""
    try:
        from backend.database import get_cursor, _use_sqlite
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii)
                       VALUES (?, 1)
                       ON CONFLICT(denumire_raw) DO UPDATE SET
                           aparitii = aparitii + 1,
                           updated_at = datetime('now')""",
                    (denumire_raw.strip(),)
                )
            else:
                cur.execute(
                    """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii)
                       VALUES (%s, 1)
                       ON CONFLICT(denumire_raw) DO UPDATE SET
                           aparitii = aparitii + 1,
                           updated_at = NOW()""",
                    (denumire_raw.strip(),)
                )
    except Exception as e:
        raw_preview = (denumire_raw or "")[:80]
        if len(denumire_raw or "") > 80:
            raw_preview += "..."
        logging.error(f"analiza_necunoscuta INSERT failed for '{raw_preview}': {e}")


def normalize_rezultat(r: RezultatParsat) -> RezultatParsat:
    """
    Cauta denumire_raw in alias-uri si seteaza analiza_standard_id.
    Daca nu gaseste, logheaza ca necunoscuta (pentru aprobare manuala).
    """
    if not r.denumire_raw:
        return r

    aid = _cauta_in_cache(r.denumire_raw)
    if aid is not None:
        r.analiza_standard_id = aid
    else:
        # Logam pentru aprobare - medicul va putea asigna ulterior
        _log_necunoscuta(r.denumire_raw)

    return r


def normalize_rezultate(lista: list[RezultatParsat]) -> list[RezultatParsat]:
    """Aplica normalizarea pe fiecare rezultat din lista."""
    return [normalize_rezultat(r) for r in lista]


def adauga_alias_nou(denumire_raw: str, analiza_standard_id: int) -> bool:
    """
    Adauga un alias nou (aprobat de medic), marcheaza necunoscuta ca aprobata
    si actualizeaza RETROACTIV toate rezultatele existente cu acel denumire_raw.
    Invalideaza cache-ul.
    """
    try:
        from backend.database import get_cursor, _use_sqlite
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    "INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) VALUES (?, ?)",
                    (analiza_standard_id, denumire_raw.strip())
                )
                cur.execute(
                    """UPDATE analiza_necunoscuta SET
                           aprobata = 1,
                           analiza_standard_id = ?,
                           updated_at = datetime('now')
                       WHERE denumire_raw = ?""",
                    (analiza_standard_id, denumire_raw.strip())
                )
                # Actualizeaza retroactiv rezultatele existente cu denumire_raw=NULL
                cur.execute(
                    "UPDATE rezultate_analize SET analiza_standard_id=? WHERE denumire_raw=? AND analiza_standard_id IS NULL",
                    (analiza_standard_id, denumire_raw.strip())
                )
            else:
                cur.execute(
                    "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
                    (analiza_standard_id, denumire_raw.strip())
                )
                cur.execute(
                    "UPDATE analiza_necunoscuta SET aprobata=1, analiza_standard_id=%s WHERE denumire_raw=%s",
                    (analiza_standard_id, denumire_raw.strip())
                )
                # Actualizeaza retroactiv rezultatele existente cu analiza_standard_id=NULL
                cur.execute(
                    "UPDATE rezultate_analize SET analiza_standard_id=%s WHERE denumire_raw=%s AND analiza_standard_id IS NULL",
                    (analiza_standard_id, denumire_raw.strip())
                )
        invalideaza_cache()
        return True
    except Exception:
        return False
