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
  7b. rapidfuzz.partial_ratio (opțional, prag 90) dacă difflib nu găsește — alias scurt în linie lungă

Daca nu gaseste nimic: salveaza in analiza_necunoscuta pentru aprobare manuala.
"""
import difflib
import logging
import re
import time
import unicodedata
from typing import Optional

from backend.models import RezultatParsat
from backend.ocr_corrections import (
    aplica_pipeline_ocr_normalizat,
    categorie_la_domeniu,
    corecteaza_ocr_linie_buletin,
    corecteaza_umar_numar_artefact_capitalizat,
)


# ─── Normalizare text ─────────────────────────────────────────────────────────

def _curata_artefacte(text: str) -> str:
    """Elimina artefacte de laborator si OCR: asteriscuri, <, >, #, blocuri [...], etc."""
    # Sterge asteriscuri, semne <> la inceput/sfarsit, artefacte comune OCR
    text = re.sub(r'[\*\<\>\#\~\^]+', ' ', text)
    # Sterge blocuri [valoare unitate] - OCR garbage (ex: "[197.52 wo/a]" lipit de denumire)
    text = re.sub(r'\s*\[\d+[.,]?\d*\s*[\w/]+\]\s*', ' ', text)
    # Sterge trailing " :" sau ":" (artefact OCR de la sfarsitul denumirii)
    text = re.sub(r'\s*:\s*$', '', text)
    text = corecteaza_umar_numar_artefact_capitalizat(text)
    text = corecteaza_ocr_linie_buletin(text)
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


def _baza_denumire_pentru_fuzzy(norm: str) -> str:
    """
    Pentru fuzzy matching: păstrează doar partea de denumire, fără sufix numeric / unități uzuale.
    `norm` trebuie deja normalizat (lowercase, fără diacritice).
    """
    if not norm:
        return norm
    t = norm.strip()
    t = re.sub(
        r"\s+[\d.,]+\s*(?:g/?d?l|mg/?l|ui/?ml|mmol/?l|µ?g/?l|/ul|%|fl|pg|umol/?l|iu/?l|m?iu/?l)?\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\s+[\d.,]+\s*$", "", t)
    return t.strip()


def _prag_fuzzy_difflib(text_norm: str) -> float:
    """Prag dinamic: denumiri scurte cer match mai strict pentru a evita false pozitive."""
    n = len(text_norm or "")
    if n < 8:
        return 0.96
    if n < 12:
        return 0.92
    return 0.89


def _prag_fuzzy_partial(text_norm: str) -> int:
    n = len(text_norm or "")
    if n < 10:
        return 97
    if n < 14:
        return 94
    return 91


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


# Cache in-memory: reîncărcare la expirare TTL sau imediat după adăugare alias (vezi invalideaza_cache()).
_CACHE: Optional[dict] = None
_CACHE_RAW: Optional[dict] = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECUNDE: int = 60  # 60 secunde — aliasurile noi din DB apar rapid; nu e nevoie de restart


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
                    from backend.database import _row_get
                    alias_val = _row_get(row, 'alias' if hasattr(row, 'keys') else 0)
                    aid_val = _row_get(row, 'analiza_standard_id' if hasattr(row, 'keys') else 1)
                    if alias_val is None or aid_val is None:
                        continue
                    alias = str(alias_val).strip()
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


def _cauta_in_cache(raw: str, categorie: Optional[str] = None) -> Optional[int]:
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
    domeniu = categorie_la_domeniu(categorie)
    raw_norm = aplica_pipeline_ocr_normalizat(_normalizeaza(raw_curat), domeniu)
    raw_fara_par = aplica_pipeline_ocr_normalizat(
        _normalizeaza(_fara_paranteze(raw_curat)), domeniu
    )

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

    # 4b. (integrat) Pipeline OCR e deja aplicat pe raw_norm / raw_fara_par mai sus.

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

    # 7. Fuzzy pe baza denumirii (fără valori numerice la coadă) — difflib
    baza_fuzz = _baza_denumire_pentru_fuzzy(raw_norm)
    if len(baza_fuzz) >= 5:
        cutoff = _prag_fuzzy_difflib(baza_fuzz)
        matches = difflib.get_close_matches(baza_fuzz, cache_norm.keys(), n=1, cutoff=cutoff)
        if matches:
            m = matches[0]
            # Pentru denumiri foarte scurte, cerem și prefix similar.
            if len(baza_fuzz) < 10 and not m.startswith(baza_fuzz[:4]):
                pass
            else:
                return cache_norm[m]

    # 7b. rapidfuzz partial_ratio pe aceeași bază; aliniere la începutul șirului
    if len(baza_fuzz) >= 6:
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            pass
        else:
            sc_cut = _prag_fuzzy_partial(baza_fuzz)
            best = process.extractOne(
                baza_fuzz,
                list(cache_norm.keys()),
                scorer=fuzz.partial_ratio,
                score_cutoff=sc_cut,
            )
            if best is not None:
                match_key, _score, _idx = best
                al = fuzz.partial_ratio_alignment(baza_fuzz, match_key)
                max_start = max(2, len(baza_fuzz) // 3)
                if al.src_start <= max_start:
                    return cache_norm[match_key]

    return None


def _log_necunoscuta(denumire_raw: str, categorie_buletin: Optional[str] = None) -> None:
    """Salveaza analiza necunoscuta in DB pentru aprobare ulterioara (cu secțiunea din PDF dacă există)."""
    try:
        from backend.database import get_cursor, _use_sqlite
        raw = denumire_raw.strip()
        cat = (categorie_buletin or "").strip() or None
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii, categorie)
                       VALUES (?, 1, ?)
                       ON CONFLICT(denumire_raw) DO UPDATE SET
                           aparitii = aparitii + 1,
                           categorie = CASE WHEN analiza_necunoscuta.categorie IS NULL
                             THEN excluded.categorie ELSE analiza_necunoscuta.categorie END,
                           updated_at = datetime('now')""",
                    (raw, cat),
                )
            else:
                cur.execute(
                    """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii, categorie)
                       VALUES (%s, 1, %s)
                       ON CONFLICT(denumire_raw) DO UPDATE SET
                           aparitii = analiza_necunoscuta.aparitii + EXCLUDED.aparitii,
                           categorie = CASE WHEN analiza_necunoscuta.categorie IS NULL
                             THEN EXCLUDED.categorie ELSE analiza_necunoscuta.categorie END,
                           updated_at = NOW()""",
                    (raw, cat),
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

    aid = _cauta_in_cache(r.denumire_raw, r.categorie)
    if aid is not None:
        r.analiza_standard_id = aid
    else:
        # Nu logăm gunoi (nume, adrese, note, OCR) — aceleași reguli ca la curățare/scripturi
        from backend.parser import este_denumire_gunoi

        if este_denumire_gunoi(r.denumire_raw):
            logging.info("[NEC_ZGOMOT] ignorat: %s", (r.denumire_raw or "")[:120])
            return r
        # Clasificare simplă pentru audit: probabil alias valid vs linie posibil coruptă
        den = (r.denumire_raw or "").strip()
        if len(den) >= 6 and re.search(r"[A-Za-zĂÂÎȘȚăâîșț]{4,}", den):
            logging.info("[NEC_PROBABIL] %s", den[:140])
        else:
            logging.info("[NEC_AMBIGUU] %s", den[:140])
        # Logam pentru aprobare - medicul va putea asigna ulterior (cu categoria din buletin)
        _log_necunoscuta(r.denumire_raw, r.categorie)

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
