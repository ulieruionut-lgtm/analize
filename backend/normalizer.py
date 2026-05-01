"""
Normalizare denumiri analize: mapare alias → analiza_standard.

Strategii de matching (in ordine, se opreste la primul match):
  1. Exact match (case-insensitive, trimmed)
  2. Exact match dupa curatare artefacte (*, <, >, #)
  3. Match normalizat (diacritice eliminate)
  4. Match fara paranteze + normalizat
  5. Match dupa primele 2 cuvinte semnificative (conservator)
  6. Match dupa >= 3 cuvinte cheie comune
  7. Fuzzy: candidați din difflib + re-ranking cu scor ponderat (ratio / partial / token_sort rapidfuzz)
  7b. rapidfuzz extract + același scor ponderat + regulă de aliniere (nu primul candidat „din întâmplare”)

La fallback global, dacă există catalog laborator (upload cu laborator_id), acel catalog primește
un mic bonus la scor pentru dezambiguizare între rețele.

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


# Override categorie urina: parametri cu acelasi nume in sange si in urina.
# Cand categorie contine 'urin', acesti termeni merg catre standardele urinare
# in loc de cele serice (Leucocite → WBC, Eritrocite → RBC etc.).
_URINA_OVERRIDE: dict[str, str] = {
    'leucocite':  'leucocite urinare',
    'eritrocite': 'eritrocite urinare',
    'hematii':    'eritrocite urinare',
    'glucoza':    'glucoza urinara',
    'proteine':   'proteine urinare',
    'bilirubina': 'bilirubina urinara',
}


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


# Ponderi fuzzy (0–100): ratio = potrivire globală, partial = OCR în șir lung,
# token_sort = cuvinte permutate („hemoglobina glicata hba1c” vs „hba1c …”).
_FUZZ_W_RATIO: float = 0.38
_FUZZ_W_PARTIAL: float = 0.32
_FUZZ_W_TOKEN_SORT: float = 0.30
# Bonus la scor (aceeași scală 0–100) pentru analize din catalogul laboratorului la pasul global.
_FUZZ_LAB_PREF_BONUS: float = 4.0


def _weighted_fuzzy_score(query: str, candidate: str) -> float:
    """
    Scor 0–100 combinând ratio, partial_ratio și token_sort_ratio (rapidfuzz).
    Fără rapidfuzz: echivalent aproximativ prin SequenceMatcher * 100.
    """
    if not query or not candidate:
        return 0.0
    try:
        from rapidfuzz import fuzz as rf

        return (
            _FUZZ_W_RATIO * float(rf.ratio(query, candidate))
            + _FUZZ_W_PARTIAL * float(rf.partial_ratio(query, candidate))
            + _FUZZ_W_TOKEN_SORT * float(rf.token_sort_ratio(query, candidate))
        )
    except ImportError:
        return float(difflib.SequenceMatcher(None, query, candidate).ratio() * 100.0)


def _fuzz_score_cu_lab(
    query: str,
    cand_key: str,
    aid: int,
    lab_preferred: Optional[frozenset[int]],
) -> float:
    sc = _weighted_fuzzy_score(query, cand_key)
    if lab_preferred is not None and aid in lab_preferred:
        sc = min(100.0, sc + _FUZZ_LAB_PREF_BONUS)
    return sc


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

# Cache denumiri standard (pentru auto-matching pas 8 — actualizat rar)
_CACHE_STD: Optional[dict] = None  # {norm_str: analiza_standard_id}
_CACHE_STD_TIMESTAMP: float = 0.0
_CACHE_STD_TTL: int = 300  # 5 minute

# Cache catalog analize per laborator (laborator_analize)
_LAB_STD_CACHE: dict[int, tuple[Optional[frozenset[int]], float]] = {}
_LAB_STD_CACHE_TTL: float = 120.0


def _lab_catalog_std_ids(laborator_id: int) -> Optional[frozenset[int]]:
    """ID-uri analiza_standard din `laborator_analize`. None = fără rânduri (nu restrânge matching)."""
    global _LAB_STD_CACHE
    try:
        lid = int(laborator_id)
    except (TypeError, ValueError):
        return None
    acum = time.time()
    ent = _LAB_STD_CACHE.get(lid)
    if ent is not None and (acum - ent[1]) < _LAB_STD_CACHE_TTL:
        return ent[0]
    try:
        from backend.database import get_analiza_standard_ids_for_laborator

        ids = get_analiza_standard_ids_for_laborator(lid)
    except Exception:
        ids = []
    frozen: Optional[frozenset[int]]
    if not ids:
        frozen = None
    else:
        frozen = frozenset(int(x) for x in ids)
    _LAB_STD_CACHE[lid] = (frozen, acum)
    return frozen


def _incarca_cache_standard() -> dict:
    """Incarca denumirile oficiale din analiza_standard pentru auto-matching la pas 8."""
    global _CACHE_STD, _CACHE_STD_TIMESTAMP
    acum = time.time()
    if _CACHE_STD is not None and (acum - _CACHE_STD_TIMESTAMP) < _CACHE_STD_TTL:
        return _CACHE_STD
    try:
        from backend.database import get_cursor, _row_get
        cache: dict = {}
        with get_cursor(commit=False) as cur:
            cur.execute("SELECT id, denumire_standard FROM analiza_standard")
            for row in cur.fetchall():
                if row is None:
                    continue
                std_id = _row_get(row, 'id' if hasattr(row, 'keys') else 0)
                denumire = _row_get(row, 'denumire_standard' if hasattr(row, 'keys') else 1)
                if std_id is not None and denumire:
                    n = _normalizeaza(str(denumire).strip())
                    if n:
                        cache[n] = int(std_id)
        _CACHE_STD = cache
        _CACHE_STD_TIMESTAMP = acum
        return cache
    except Exception as e:
        logging.warning("[AUTO-ALIAS] Eroare incarcare cache standard: %s", e)
        return {}


def _invalideaza_cache_standard() -> None:
    global _CACHE_STD, _CACHE_STD_TIMESTAMP
    _CACHE_STD = None
    _CACHE_STD_TIMESTAMP = 0.0


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
    global _CACHE, _CACHE_RAW, _CACHE_TIMESTAMP, _LAB_STD_CACHE
    _CACHE = None
    _CACHE_RAW = None
    _CACHE_TIMESTAMP = 0.0
    _LAB_STD_CACHE = {}


def _auto_salveaza_alias(denumire_raw: str, analiza_standard_id: int) -> None:
    """
    Salveaza automat un alias descoperit la pasul 8 (fuzzy pe analiza_standard).
    Foloseste adauga_alias_nou() pentru alias + actualizare retroactiva + invalidare cache.
    """
    try:
        ok = adauga_alias_nou(denumire_raw.strip(), analiza_standard_id)
        if ok:
            logging.info("[AUTO-ALIAS] Salvat: %r → std_id=%d", denumire_raw[:80], analiza_standard_id)
        _invalideaza_cache_standard()
    except Exception as e:
        logging.warning("[AUTO-ALIAS] Eroare salvare: %s", e)


def _aid_passes_lab(aid: int, lab_allowed: Optional[frozenset[int]]) -> bool:
    return lab_allowed is None or aid in lab_allowed


def _heuristic_alias_and_std_match(
    raw_norm: str,
    raw_curat: str,
    cache_norm: dict,
    lab_allowed: Optional[frozenset[int]],
    lab_preferred: Optional[frozenset[int]] = None,
) -> Optional[int]:
    """
    Pașii 5–8: euristici pe alias, fuzzy, apoi match pe `analiza_standard`.
    Dacă `lab_allowed` e setat, se consideră doar candidați din catalogul laboratorului
    (reduce confuzii între rețele); apelantul poate relua fără filtru ca fallback.
    `lab_preferred`: la fallback global, bonus de scor pentru ID-uri din acest catalog (dezambiguizare).
    """
    # 5. Match dupa primele 2 cuvinte semnificative (mai conservator)
    cuvinte = [w for w in re.split(r'[\s\-/\(\)]+', raw_norm) if len(w) >= 3 and not w.isdigit()]
    if len(cuvinte) >= 2:
        first_two = cuvinte[:2]
        for alias_norm, aid in cache_norm.items():
            if not _aid_passes_lab(aid, lab_allowed):
                continue
            alias_cuvinte = [w for w in re.split(r'[\s\-/\(\)]+', alias_norm)
                             if len(w) >= 3 and not w.isdigit()]
            if len(alias_cuvinte) >= 2 and alias_cuvinte[:2] == first_two:
                return aid

    # 6. Match dupa cuvinte cheie comune (>= 3 cuvinte comune, evita false pozitive)
    raw_kw = _cuvinte_cheie(raw_norm)
    if len(raw_kw) >= 3:
        for alias_norm, aid in cache_norm.items():
            if not _aid_passes_lab(aid, lab_allowed):
                continue
            alias_kw = _cuvinte_cheie(alias_norm)
            if len(raw_kw & alias_kw) >= 3:
                return aid

    baza_fuzz = _baza_denumire_pentru_fuzzy(raw_norm)
    min_prefix = 4 if len(baza_fuzz) < 10 else 3

    # 7. Fuzzy pe baza denumirii — difflib pentru candidați, apoi cel mai bun scor ponderat
    if len(baza_fuzz) >= 5:
        cutoff = _prag_fuzzy_difflib(baza_fuzz)
        matches = difflib.get_close_matches(baza_fuzz, cache_norm.keys(), n=24, cutoff=cutoff)
        best_aid: Optional[int] = None
        best_sc = -1.0
        best_tie = (9999, 0)  # (|len diff|, -partial proxy) — minim e mai bun
        for m in matches:
            aid = cache_norm[m]
            if not _aid_passes_lab(aid, lab_allowed):
                continue
            if len(baza_fuzz) < 10 and not m.startswith(baza_fuzz[:min_prefix]):
                continue
            sc = _fuzz_score_cu_lab(baza_fuzz, m, aid, lab_preferred)
            ld = abs(len(m) - len(baza_fuzz))
            tie = (ld, -int(difflib.SequenceMatcher(None, baza_fuzz, m).ratio() * 100))
            if sc > best_sc or (abs(sc - best_sc) < 0.25 and tie < best_tie):
                best_sc, best_aid, best_tie = sc, aid, tie
        if best_aid is not None:
            return best_aid

    # 7b. rapidfuzz partial_ratio — mai mulți candidați, alegere după scor ponderat + aliniere
    if len(baza_fuzz) >= 6:
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            pass
        else:
            sc_cut = _prag_fuzzy_partial(baza_fuzz)
            keys_list = list(cache_norm.keys())
            cands = process.extract(
                baza_fuzz,
                keys_list,
                scorer=fuzz.partial_ratio,
                score_cutoff=sc_cut,
                limit=20,
            )
            best_aid = None
            best_sc = -1.0
            best_tie = (9999, 0)
            for match_key, partial_sc, _idx in cands or []:
                aid = cache_norm[match_key]
                if not _aid_passes_lab(aid, lab_allowed):
                    continue
                al = fuzz.partial_ratio_alignment(baza_fuzz, match_key)
                max_start = max(2, len(baza_fuzz) // 3)
                if al.src_start > max_start:
                    continue
                sc = _fuzz_score_cu_lab(baza_fuzz, match_key, aid, lab_preferred)
                ld = abs(len(match_key) - len(baza_fuzz))
                tie = (ld, -partial_sc)
                if sc > best_sc or (abs(sc - best_sc) < 0.25 and tie < best_tie):
                    best_sc, best_aid, best_tie = sc, aid, tie
            if best_aid is not None:
                return best_aid

    # 8. Auto-match direct pe denumiri din analiza_standard (fallback final cu auto-salvare alias).
    if len(baza_fuzz) >= 5:
        std_cache_full = _incarca_cache_standard()
        if std_cache_full:
            if lab_allowed:
                std_cache = {k: v for k, v in std_cache_full.items() if v in lab_allowed}
            else:
                std_cache = dict(std_cache_full)
            if std_cache:
                cutoff8 = _prag_fuzzy_difflib(baza_fuzz)
                matches8 = difflib.get_close_matches(baza_fuzz, std_cache.keys(), n=24, cutoff=cutoff8)
                best_id: Optional[int] = None
                best_sc = -1.0
                best_tie = (9999, 0)
                for m8 in matches8:
                    if len(baza_fuzz) < 10 and not m8.startswith(baza_fuzz[:min_prefix]):
                        continue
                    std_id = std_cache[m8]
                    sc = _fuzz_score_cu_lab(baza_fuzz, m8, std_id, lab_preferred)
                    ld = abs(len(m8) - len(baza_fuzz))
                    tie = (ld, -int(difflib.SequenceMatcher(None, baza_fuzz, m8).ratio() * 100))
                    if sc > best_sc or (abs(sc - best_sc) < 0.25 and tie < best_tie):
                        best_sc, best_id, best_tie = sc, std_id, tie
                if best_id is not None:
                    _auto_salveaza_alias(raw_curat, best_id)
                    return best_id
                if len(baza_fuzz) >= 6:
                    try:
                        from rapidfuzz import fuzz as _fuzz, process as _proc
                        sc_cut8 = _prag_fuzzy_partial(baza_fuzz)
                        cands8 = _proc.extract(
                            baza_fuzz,
                            list(std_cache.keys()),
                            scorer=_fuzz.partial_ratio,
                            score_cutoff=sc_cut8,
                            limit=20,
                        )
                        best_id = None
                        best_sc = -1.0
                        best_tie = (9999, 0)
                        for mk8, partial_sc8, _idx8 in cands8 or []:
                            al8 = _fuzz.partial_ratio_alignment(baza_fuzz, mk8)
                            if al8.src_start > max(2, len(baza_fuzz) // 3):
                                continue
                            std_id = std_cache[mk8]
                            sc = _fuzz_score_cu_lab(baza_fuzz, mk8, std_id, lab_preferred)
                            ld = abs(len(mk8) - len(baza_fuzz))
                            tie = (ld, -partial_sc8)
                            if sc > best_sc or (abs(sc - best_sc) < 0.25 and tie < best_tie):
                                best_sc, best_id, best_tie = sc, std_id, tie
                        if best_id is not None:
                            _auto_salveaza_alias(raw_curat, best_id)
                            return best_id
                    except ImportError:
                        pass

    return None


def _cauta_in_cache(
    raw: str,
    categorie: Optional[str] = None,
    laborator_id: Optional[int] = None,
) -> Optional[int]:
    """
    Incearca mai multe strategii de matching si returneaza analiza_standard_id sau None.
    Dacă `laborator_id` e setat și există rânduri în `laborator_analize`, pașii 5–8 rulează
    întâi restrânși la acel catalog; dacă nu găsesc nimic, se repetă pașii 5–8 pe tot setul
    (comportament identic cu versiunea anterioară).
    """
    cache_norm, cache_raw = _incarca_cache()
    if not cache_norm:
        return None

    raw = raw.strip()
    raw = _strip_prefix_regina_maria(raw)
    raw_curat = _curata_artefacte(raw)
    raw_lower = raw_curat.lower()
    domeniu = categorie_la_domeniu(categorie)
    raw_norm = aplica_pipeline_ocr_normalizat(_normalizeaza(raw_curat), domeniu)
    raw_fara_par = aplica_pipeline_ocr_normalizat(
        _normalizeaza(_fara_paranteze(raw_curat)), domeniu
    )

    # 0. Override categorie urina
    if categorie and re.search(r'urin', categorie, re.IGNORECASE):
        raw_norm_base = _normalizeaza(_fara_paranteze(raw_curat))
        urina_std_name = _URINA_OVERRIDE.get(raw_norm_base)
        if urina_std_name:
            std_cache = _incarca_cache_standard()
            urina_std_norm = _normalizeaza(urina_std_name)
            if urina_std_norm in std_cache:
                return std_cache[urina_std_norm]

    # 1–4. Match exact (alias global) — neschimbat, indiferent de laborator
    if raw.lower() in cache_raw:
        return cache_raw[raw.lower()]
    if raw_lower in cache_raw:
        return cache_raw[raw_lower]
    if raw_norm in cache_norm:
        return cache_norm[raw_norm]
    if raw_fara_par and raw_fara_par in cache_norm:
        return cache_norm[raw_fara_par]

    # 0b. MedLife: descrieri urocultură pe rând propriu (OCR trunchiat / fără alias dedicat)
    raw_n2 = _normalizeaza(raw_curat)
    if "rezultatcantitativ" in raw_n2.replace(" ", "") and "bacteriurie" in raw_n2:
        for probe in ("urocultură", "urocultura"):
            pn = _normalizeaza(probe)
            if pn in cache_norm:
                return cache_norm[pn]
    if raw_n2.startswith("organisme absente") or raw_n2.startswith("organismeabsente"):
        for probe in ("urocultură", "urocultura"):
            pn = _normalizeaza(probe)
            if pn in cache_norm:
                return cache_norm[pn]

    lab_subset: Optional[frozenset[int]] = None
    if laborator_id is not None:
        lab_subset = _lab_catalog_std_ids(int(laborator_id))

    if lab_subset and len(lab_subset) > 0:
        hit = _heuristic_alias_and_std_match(
            raw_norm, raw_curat, cache_norm, lab_subset, lab_preferred=None
        )
        if hit is not None:
            return hit

    return _heuristic_alias_and_std_match(
        raw_norm, raw_curat, cache_norm, None, lab_preferred=lab_subset
    )


def _log_necunoscuta(
    denumire_raw: str,
    categorie_buletin: Optional[str] = None,
    laborator_id: Optional[int] = None,
) -> None:
    """Salvează analiza necunoscută pentru aprobare; păstrează `laborator_id` pentru auto-rezolvare contextuală."""
    try:
        from backend.database import get_cursor, _use_sqlite
        raw = denumire_raw.strip()
        cat = (categorie_buletin or "").strip() or None
        lab: Optional[int] = None
        if laborator_id is not None:
            try:
                lab = int(laborator_id)
            except (TypeError, ValueError):
                lab = None
        with get_cursor() as cur:
            if _use_sqlite():
                try:
                    cur.execute(
                        """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii, categorie, laborator_id)
                           VALUES (?, 1, ?, ?)
                           ON CONFLICT(denumire_raw) DO UPDATE SET
                               aparitii = aparitii + 1,
                               categorie = CASE WHEN analiza_necunoscuta.categorie IS NULL
                                 THEN excluded.categorie ELSE analiza_necunoscuta.categorie END,
                               laborator_id = COALESCE(excluded.laborator_id, analiza_necunoscuta.laborator_id),
                               updated_at = datetime('now')""",
                        (raw, cat, lab),
                    )
                except Exception as ex:
                    if "laborator_id" not in str(ex).lower():
                        raise
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
                try:
                    cur.execute(
                        """INSERT INTO analiza_necunoscuta (denumire_raw, aparitii, categorie, laborator_id)
                           VALUES (%s, 1, %s, %s)
                           ON CONFLICT(denumire_raw) DO UPDATE SET
                               aparitii = analiza_necunoscuta.aparitii + EXCLUDED.aparitii,
                               categorie = CASE WHEN analiza_necunoscuta.categorie IS NULL
                                 THEN EXCLUDED.categorie ELSE analiza_necunoscuta.categorie END,
                               laborator_id = COALESCE(EXCLUDED.laborator_id, analiza_necunoscuta.laborator_id),
                               updated_at = NOW()""",
                        (raw, cat, lab),
                    )
                except Exception as ex:
                    if "laborator_id" not in str(ex).lower() and "undefinedcolumn" not in str(ex).lower():
                        raise
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
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


def normalize_rezultat(r: RezultatParsat, laborator_id: Optional[int] = None) -> RezultatParsat:
    """
    Cauta denumire_raw in alias-uri si seteaza analiza_standard_id.
    Daca nu gaseste, logheaza ca necunoscuta (pentru aprobare manuala).
    """
    if not r.denumire_raw:
        return r

    aid = _cauta_in_cache(r.denumire_raw, r.categorie, laborator_id)
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
        _log_necunoscuta(r.denumire_raw, r.categorie, laborator_id)

    return r


_RE_VALOARE_TEXT_LT_GT = re.compile(
    r"^([<>≤≥]=?)\s*([\d.,]+)\s*$"
)


def _aplica_flag_din_valoare_text(r: RezultatParsat) -> None:
    """
    Dacă valoarea e stocată ca text cu prefix '<' sau '>' (ex: '< 50', '> 0.12'),
    extrage valoarea numerică în r.valoare și setează flag-ul L/H corespunzător
    față de intervalul de referință. Folosit pentru MedLife PDR / Synevo / Regina Maria.
    """
    vt = (r.valoare_text or "").strip()
    if not vt or r.valoare is not None:
        return
    m = _RE_VALOARE_TEXT_LT_GT.match(vt)
    if not m:
        return
    op, num_s = m.group(1), m.group(2).replace(",", ".")
    try:
        num = float(num_s)
    except ValueError:
        return
    r.valoare = num
    # Determina flag fata de interval
    if op in ("<", "≤", "<="):
        # Valoarea e sub limita raportata: daca e sub minimul de referinta → L
        if r.interval_min is not None and num < r.interval_min:
            r.flag = r.flag or "L"
        else:
            r.flag = r.flag or "L"  # "<X" implicit L (sub limita de detectie)
    elif op in (">", "≥", ">="):
        if r.interval_max is not None and num > r.interval_max:
            r.flag = r.flag or "H"
        else:
            r.flag = r.flag or "H"


def normalize_rezultate(
    lista: list[RezultatParsat],
    laborator_id: Optional[int] = None,
) -> list[RezultatParsat]:
    """Aplica normalizarea pe fiecare rezultat din lista."""
    rezultate = [normalize_rezultat(r, laborator_id) for r in lista]
    for r in rezultate:
        _aplica_flag_din_valoare_text(r)
    return rezultate


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


def adauga_aliasuri_bulk(denumiri_raw: list[str], analiza_standard_id: int) -> dict:
    """
    Aceeași logică ca ``adauga_alias_nou`` pentru mai multe denumiri într-o singură tranzacție:
    alias în analiza_alias, marchează necunoscute, UPDATE retroactiv pe rezultate_analize.
    """
    seen: set[str] = set()
    items: list[str] = []
    for d in denumiri_raw or []:
        s = (d or "").strip()
        if s and s not in seen:
            seen.add(s)
            items.append(s)
    if not items:
        return {"ok": True, "processed": 0, "unique_strings": 0}

    try:
        from backend.database import get_cursor, _use_sqlite

        with get_cursor() as cur:
            if _use_sqlite():
                for s in items:
                    cur.execute(
                        "INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) VALUES (?, ?)",
                        (analiza_standard_id, s),
                    )
                    cur.execute(
                        """UPDATE analiza_necunoscuta SET
                               aprobata = 1,
                               analiza_standard_id = ?,
                               updated_at = datetime('now')
                           WHERE denumire_raw = ?""",
                        (analiza_standard_id, s),
                    )
                    cur.execute(
                        "UPDATE rezultate_analize SET analiza_standard_id=? "
                        "WHERE denumire_raw=? AND analiza_standard_id IS NULL",
                        (analiza_standard_id, s),
                    )
            else:
                for s in items:
                    cur.execute(
                        "INSERT INTO analiza_alias (analiza_standard_id, alias) "
                        "VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
                        (analiza_standard_id, s),
                    )
                    cur.execute(
                        "UPDATE analiza_necunoscuta SET aprobata=1, analiza_standard_id=%s "
                        "WHERE denumire_raw=%s",
                        (analiza_standard_id, s),
                    )
                    cur.execute(
                        "UPDATE rezultate_analize SET analiza_standard_id=%s "
                        "WHERE denumire_raw=%s AND analiza_standard_id IS NULL",
                        (analiza_standard_id, s),
                    )
        invalideaza_cache()
        return {"ok": True, "processed": len(items), "unique_strings": len(items)}
    except Exception as e:
        logging.exception("adauga_aliasuri_bulk: %s", e)
        return {"ok": False, "processed": 0, "unique_strings": 0, "error": str(e)[:500]}


def auto_rezolva_necunoscute() -> dict:
    """
    Parcurge toate intrarile neaprobate din analiza_necunoscuta si incearca
    auto-matching pe analiza_standard (pasul 8 din _cauta_in_cache).
    Daca gaseste match cu scor suficient → salveaza alias + actualizare retroactiva.
    Returneaza: {procesate, rezolvate, nerezolvate, erori}
    """
    try:
        from backend.database import get_cursor, _use_sqlite, _row_get
        with get_cursor(commit=False) as cur:
            if _use_sqlite():
                try:
                    cur.execute(
                        "SELECT id, denumire_raw, categorie, laborator_id FROM analiza_necunoscuta "
                        "WHERE aprobata = 0 OR aprobata IS NULL"
                    )
                except Exception:
                    cur.execute(
                        "SELECT id, denumire_raw, categorie FROM analiza_necunoscuta "
                        "WHERE aprobata = 0 OR aprobata IS NULL"
                    )
            else:
                try:
                    cur.execute(
                        "SELECT id, denumire_raw, categorie, laborator_id FROM analiza_necunoscuta "
                        "WHERE aprobata IS DISTINCT FROM 1"
                    )
                except Exception:
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
                    cur.execute(
                        "SELECT id, denumire_raw, categorie FROM analiza_necunoscuta "
                        "WHERE aprobata IS DISTINCT FROM 1"
                    )
            rows = cur.fetchall()
    except Exception as e:
        return {"ok": False, "procesate": 0, "rezolvate": 0, "nerezolvate": 0, "erori": [str(e)[:200]]}

    procesate = 0
    rezolvate = 0
    erori: list[str] = []

    for row in rows:
        try:
            denumire = str(_row_get(row, "denumire_raw") or "").strip()
            categorie = str(_row_get(row, "categorie") or "").strip() or None
            lab_row = _row_get(row, "laborator_id")
            lab_ctx: Optional[int] = None
            if lab_row is not None:
                try:
                    lab_ctx = int(lab_row)
                except (TypeError, ValueError):
                    lab_ctx = None
            if not denumire:
                continue
            procesate += 1
            std_id = _cauta_in_cache(denumire, categorie, lab_ctx)
            if std_id is not None:
                # _cauta_in_cache a apelat deja _auto_salveaza_alias intern la pasul 8
                # dar daca a gasit prin alt pas (1-7), apelam explicit adauga_alias_nou
                adauga_alias_nou(denumire, std_id)
                rezolvate += 1
        except Exception as e:
            erori.append(str(e)[:150])

    return {
        "ok": True,
        "procesate": procesate,
        "rezolvate": rezolvate,
        "nerezolvate": procesate - rezolvate,
        "erori": erori[:20],
    }
