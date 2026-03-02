"""
Normalizare denumiri analize: mapare alias → analiza_standard.

Strategii de matching (in ordine, se opreste la primul match):
  1. Exact match (case-insensitive, trimmed)
  2. Match dupa normalizare diacritice (ă→a, î→i, etc.)
  3. Match dupa normalizare + eliminare paranteze si cod
  4. Match substring bidirectional (alias contine raw sau invers)
  5. Match dupa primul cuvant semnificativ

Daca nu gaseste nimic: salveaza in analiza_necunoscuta pentru aprobare manuala.
"""
import re
import unicodedata
from typing import Optional

from backend.models import RezultatParsat


# ─── Normalizare text ─────────────────────────────────────────────────────────

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


# Cache in-memory pentru alias-uri (evita query-uri repetate la DB)
_CACHE: Optional[dict] = None   # { text_normalizat: analiza_standard_id }
_CACHE_RAW: Optional[dict] = None  # { alias_original_lower: id }


def _incarca_cache() -> tuple[dict, dict]:
    global _CACHE, _CACHE_RAW
    if _CACHE is not None:
        return _CACHE, _CACHE_RAW
    try:
        from backend.database import get_cursor, _use_sqlite
        cache_norm = {}
        cache_raw = {}
        with get_cursor(commit=False) as cur:
            cur.execute("SELECT alias, analiza_standard_id FROM analiza_alias")
            for row in cur.fetchall():
                alias = str(row[0] if _use_sqlite() else row['alias'])
                aid = int(row[1] if _use_sqlite() else row['analiza_standard_id'])
                cache_raw[alias.lower()] = aid
                cache_norm[_normalizeaza(alias)] = aid
        _CACHE = cache_norm
        _CACHE_RAW = cache_raw
        return _CACHE, _CACHE_RAW
    except Exception:
        return {}, {}


def invalideaza_cache():
    """Apelat dupa ce se adauga un alias nou."""
    global _CACHE, _CACHE_RAW
    _CACHE = None
    _CACHE_RAW = None


def _cauta_in_cache(raw: str) -> Optional[int]:
    """
    Incearca mai multe strategii de matching si returneaza analiza_standard_id sau None.
    """
    cache_norm, cache_raw = _incarca_cache()
    if not cache_norm:
        return None

    raw = raw.strip()
    raw_lower = raw.lower()
    raw_norm = _normalizeaza(raw)
    raw_fara_par = _normalizeaza(_fara_paranteze(raw))

    # 1. Exact match (case-insensitive)
    if raw_lower in cache_raw:
        return cache_raw[raw_lower]

    # 2. Match normalizat (diacritice eliminate)
    if raw_norm in cache_norm:
        return cache_norm[raw_norm]

    # 3. Match fara paranteze
    if raw_fara_par and raw_fara_par in cache_norm:
        return cache_norm[raw_fara_par]

    # 4. Match dupa primul cuvant semnificativ (>= 3 litere)
    cuvinte = [w for w in re.split(r'[\s\-/\(\)]+', raw_norm) if len(w) >= 3 and not w.isdigit()]
    if cuvinte:
        # Cauta alias-uri care incep cu sau contin primul cuvant
        prim = cuvinte[0]
        for alias_norm, aid in cache_norm.items():
            alias_cuvinte = alias_norm.split()
            if alias_cuvinte and alias_cuvinte[0] == prim:
                return aid

    # 5. Substring bidirectional: raw contine alias sau alias contine raw
    # (doar pentru texte cu >= 4 caractere, evita false positive)
    if len(raw_norm) >= 4:
        for alias_norm, aid in cache_norm.items():
            if len(alias_norm) >= 4:
                if raw_norm in alias_norm or alias_norm in raw_norm:
                    return aid

    # 6. Match dupa cuvinte cheie comune (>= 2 cuvinte comune)
    raw_kw = _cuvinte_cheie(raw_norm)
    if len(raw_kw) >= 2:
        for alias_norm, aid in cache_norm.items():
            alias_kw = _cuvinte_cheie(alias_norm)
            if len(raw_kw & alias_kw) >= 2:
                return aid

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
    except Exception:
        pass  # Nu blocam upload-ul pentru o eroare de logging


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
    Adauga un alias nou (aprobat de medic) si marcheaza necunoscuta ca aprobata.
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
            else:
                cur.execute(
                    "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (analiza_standard_id, denumire_raw.strip())
                )
                cur.execute(
                    "UPDATE analiza_necunoscuta SET aprobata=1, analiza_standard_id=%s WHERE denumire_raw=%s",
                    (analiza_standard_id, denumire_raw.strip())
                )
        invalideaza_cache()
        return True
    except Exception:
        return False
