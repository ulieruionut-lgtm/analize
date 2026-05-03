"""Router pacienti: cautare, evolutie matrice, laboratoare."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.database import (
    get_buletine_recente,
    get_laborator_analize,
    get_laboratoare,
    get_pacient_cu_analize,
    get_pacienti_paginat,
    update_pacient_nume,
)
from backend.deps import get_current_user
from backend.utils import normalizare_data_text

router = APIRouter()

# Ordinea categoriilor in tabelul de evolutie
_ORDINE_CATEGORIE = {
    "Hemoleucograma": 0,
    "Biochimie": 1,
    "Lipidograma": 2,
    "Coagulare": 3,
    "Examen urina": 4,
    "Examen urina sediment": 4,
    "Examen urina biochimie": 4,
    "Electroforeza": 5,
    "Imunologie si Serologie": 6,
    "Hormoni tiroidieni": 7,
    "Hormoni": 8,
    "Markeri tumorali": 9,
    "Minerale si electroliti": 10,
    "Inflamatie": 11,
}


@router.get("/buletine/recente")
async def buletine_recente(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Ultimele `limit` buletine incarcate (implicit 20), cu info pacient."""
    return get_buletine_recente(limit=limit)


@router.get("/pacienti")
async def lista_pacienti(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Lista pacienti paginata. ?q=text pentru cautare, ?limit=50&offset=0 pentru paginare."""
    items, total = get_pacienti_paginat(limit=limit, offset=offset, q=q)
    return {"items": items, "total": total}


def _buletin_sort_key(b: dict) -> tuple:
    """Cheie sortare: data buletinului (desc), apoi moment încărcare (desc).
    La două buletine cu aceeași dată clinică, prima coloană = ultima încărcare pe server."""
    d_raw = b.get("data_buletin")
    d = ""
    if d_raw:
        ds = str(d_raw)
        if "T" in ds:
            d = ds.split("T")[0]
        elif " " in ds and ":" in ds:
            d = ds.split(" ")[0]
        else:
            d = ds.strip()[:32]
    c_raw = b.get("created_at")
    c = str(c_raw) if c_raw is not None else ""
    # Fără dată pe buletin: ordonăm doar după upload
    primary = d or c
    return (primary, c)


@router.get("/pacient/{cnp}/evolutie-matrice")
async def get_pacient_evolutie_matrice(cnp: str, current_user: dict = Depends(get_current_user)):
    """
    Returneaza matricea de evolutie pentru pacient: analize pe randuri, date pe coloane.
    Format: {pacient: {...}, date_buletine: [...], analize: [{denumire, unitate, valori[], flags[]}]}
    """
    pacient_data = get_pacient_cu_analize(cnp)
    if not pacient_data:
        raise HTTPException(status_code=404, detail="Pacient negasit.")

    buletine = pacient_data.get("buletine", [])
    buletine_sorted = sorted(buletine, key=_buletin_sort_key, reverse=True)

    date_buletine = []
    for b in buletine_sorted:
        data = b.get("data_buletin") or b.get("created_at") or ""
        if data:
            if "T" in data:
                data = data.split("T")[0]
            elif " " in data and ":" in data:
                data = data.split(" ")[0]
            data = normalizare_data_text(data)
        date_buletine.append(data or "Necunoscuta")

    n_buletine = len(buletine_sorted)
    analize_map = {}

    for idx_buletin, b in enumerate(buletine_sorted):
        buletin_id = b.get("id")
        aparitii_sid: dict[int, int] = {}
        aparitii_unknown: dict[str, int] = {}
        for rez in b.get("rezultate", []):
            raw = (rez.get("denumire_raw") or "").strip()
            sid = rez.get("analiza_standard_id")
            std = (rez.get("denumire_standard") or "").strip()
            rid = rez.get("id")
            if n_buletine == 1 and rid is not None:
                cheie = ("rez", int(rid))
            else:
                if sid is not None:
                    try:
                        sid_int = int(sid)
                    except (TypeError, ValueError):
                        sid_int = 0
                    aparitie = aparitii_sid.get(sid_int, 0)
                    aparitii_sid[sid_int] = aparitie + 1
                    cheie = ("m", sid_int, aparitie)
                else:
                    unk_label = re.sub(r"\s+", " ", (raw or std or "Necunoscuta").strip()).lower()
                    aparitie = aparitii_unknown.get(unk_label, 0)
                    aparitii_unknown[unk_label] = aparitie + 1
                    cheie = ("u", unk_label, aparitie)

            if cheie not in analize_map:
                label = (raw or std or "?").strip()
                analize_map[cheie] = {
                    "denumire_standard": label,
                    "unitate": rez.get("unitate") or "",
                    "valori_dict": {},
                    "categorie": rez.get("categorie") or "",
                    "ordine_min": rez.get("ordine") if rez.get("ordine") is not None else 99999,
                }
            else:
                ord_curent = rez.get("ordine")
                if ord_curent is not None and ord_curent < analize_map[cheie]["ordine_min"]:
                    analize_map[cheie]["ordine_min"] = ord_curent
                if not analize_map[cheie]["categorie"] and rez.get("categorie"):
                    analize_map[cheie]["categorie"] = rez.get("categorie") or ""

            valoare = rez.get("valoare")
            if valoare is None and rez.get("valoare_text"):
                valoare = rez.get("valoare_text")
            analize_map[cheie]["valori_dict"][buletin_id] = (valoare, rez.get("flag") or "")

    def _sort_key(cheie_info):
        cheie, info = cheie_info
        cat = info.get("categorie") or ""
        ord_cat = _ORDINE_CATEGORIE.get(cat, 999)
        ord_pdf = info.get("ordine_min", 99999)
        return (ord_cat, ord_pdf, info["denumire_standard"].lower())

    analize_result = []
    for cheie, info in sorted(analize_map.items(), key=_sort_key):
        valori = []
        flags = []
        for b in buletine_sorted:
            bid = b.get("id")
            if bid in info["valori_dict"]:
                val, flag = info["valori_dict"][bid]
                valori.append(val)
                flags.append(flag)
            else:
                valori.append(None)
                flags.append("")
        analize_result.append({
            "denumire_standard": info["denumire_standard"],
            "unitate": info["unitate"],
            "valori": valori,
            "flags": flags,
            "categorie": info.get("categorie") or "",
            "ordine_pdf": info.get("ordine_min", 99999),
        })

    def _is_missing(v) -> bool:
        return v is None or (isinstance(v, str) and not v.strip())

    def _norm_cmp(v) -> str:
        if _is_missing(v):
            return ""
        return re.sub(r"\s+", " ", str(v).strip())

    # Compactare randuri complementare
    merged_result = []
    for row in analize_result:
        den = (row.get("denumire_standard") or "").strip().lower()
        unt = (row.get("unitate") or "").strip().lower()
        cat = (row.get("categorie") or "").strip().lower()
        valori_row = list(row.get("valori") or [])
        flags_row = list(row.get("flags") or [])
        merged = False
        for target in merged_result:
            t_den = (target.get("denumire_standard") or "").strip().lower()
            t_unt = (target.get("unitate") or "").strip().lower()
            t_cat = (target.get("categorie") or "").strip().lower()
            if (den, unt, cat) != (t_den, t_unt, t_cat):
                continue
            compat = True
            t_valori = target.get("valori") or []
            t_flags = target.get("flags") or []
            for i in range(min(len(valori_row), len(t_valori))):
                v_new, v_old = valori_row[i], t_valori[i]
                if not _is_missing(v_new) and not _is_missing(v_old) and _norm_cmp(v_new) != _norm_cmp(v_old):
                    compat = False
                    break
                f_new, f_old = flags_row[i], t_flags[i]
                if not _is_missing(f_new) and not _is_missing(f_old) and _norm_cmp(f_new) != _norm_cmp(f_old):
                    compat = False
                    break
            if not compat:
                continue
            for i in range(min(len(valori_row), len(t_valori))):
                if _is_missing(t_valori[i]) and not _is_missing(valori_row[i]):
                    t_valori[i] = valori_row[i]
                if _is_missing(t_flags[i]) and not _is_missing(flags_row[i]):
                    t_flags[i] = flags_row[i]
            target["valori"] = t_valori
            target["flags"] = t_flags
            merged = True
            break
        if not merged:
            merged_result.append(row)
    analize_result = merged_result

    # Colaps: același text de afișare poate veni de la contexte diferite (ex. Eritrocite sumar vs
    # sediment). Fără categorie + ordine, «un singur rând per denumire» pierdea ~3 analize (17 vs 20).
    def _pick_best_value(values: list):
        valid = [v for v in values if not _is_missing(v)]
        if not valid:
            return None
        numeric = []
        texty = []
        for v in valid:
            if isinstance(v, (int, float)):
                numeric.append(v)
                continue
            s = _norm_cmp(v)
            try:
                numeric.append(float(s.replace(",", ".")))
            except (TypeError, ValueError):
                texty.append(s)
        if numeric:
            return numeric[0]
        texty = [t for t in texty if t]
        if not texty:
            return None
        return sorted(texty, key=lambda t: (len(t), t))[0]

    def _pick_best_flag(flags: list):
        valid = [_norm_cmp(f) for f in flags if not _is_missing(f)]
        return valid[0] if valid else ""

    collapsed: dict[tuple, dict] = {}
    for row in analize_result:
        den = (row.get("denumire_standard") or "").strip().lower()
        cat = (row.get("categorie") or "").strip().lower()
        unt = (row.get("unitate") or "").strip().lower()
        try:
            ord_pdf = int(row.get("ordine_pdf") if row.get("ordine_pdf") is not None else 99999)
        except (TypeError, ValueError):
            ord_pdf = 99999
        key = (den, cat, unt, ord_pdf)
        if key not in collapsed:
            collapsed[key] = {
                "denumire_standard": row.get("denumire_standard"),
                "unitate": row.get("unitate"),
                "categorie": row.get("categorie"),
                "valori": list(row.get("valori") or []),
                "flags": list(row.get("flags") or []),
                "ordine_pdf": ord_pdf,
            }
            continue
        target = collapsed[key]
        t_vals = target.get("valori") or []
        t_flags = target.get("flags") or []
        s_vals = list(row.get("valori") or [])
        s_flags = list(row.get("flags") or [])
        n = min(len(t_vals), len(s_vals))
        for i in range(n):
            t_vals[i] = _pick_best_value([t_vals[i], s_vals[i]])
            t_flags[i] = _pick_best_flag([t_flags[i], s_flags[i]])
        target["valori"] = t_vals
        target["flags"] = t_flags

    analize_result = sorted(
        collapsed.values(),
        key=lambda r: (
            _ORDINE_CATEGORIE.get((r.get("categorie") or "").strip(), 999),
            int(r.get("ordine_pdf") or 99999) if isinstance(r.get("ordine_pdf"), (int, float)) else 99999,
            (r.get("denumire_standard") or "").lower(),
        ),
    )
    for r in analize_result:
        r.pop("ordine_pdf", None)
    rezultate_in_baza = sum(len(b.get("rezultate") or []) for b in buletine_sorted)

    return {
        "pacient": {
            "id": pacient_data.get("id"),
            "cnp": pacient_data.get("cnp"),
            "nume": pacient_data.get("nume"),
            "prenume": pacient_data.get("prenume"),
        },
        "date_buletine": date_buletine,
        "buletine_ids": [b.get("id") for b in buletine_sorted],
        "rezultate_in_baza": rezultate_in_baza,
        "analize": analize_result,
    }


@router.get("/pacient/{cnp}")
async def get_pacient(cnp: str, current_user: dict = Depends(get_current_user)):
    """Pacientul cu CNP dat + toate buletinele + rezultatele."""
    result = get_pacient_cu_analize(cnp)
    if not result:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return result


@router.patch("/pacient/{cnp}")
async def actualizeaza_pacient_nume(cnp: str, body: dict, current_user: dict = Depends(get_current_user)):
    """Actualizeaza numele si/sau prenumele unui pacient."""
    nume = (body.get("nume") or "").strip()
    prenume = body.get("prenume")
    if prenume is not None:
        prenume = str(prenume).strip() or None
    if not nume:
        raise HTTPException(status_code=400, detail="Numele nu poate fi gol.")
    ok = update_pacient_nume(cnp, nume, prenume)
    if not ok:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return {"message": "Nume actualizat.", "pacient": get_pacient_cu_analize(cnp)}


@router.get("/laboratoare")
async def lista_laboratoare(current_user: dict = Depends(get_current_user)):
    """Lista laboratoare cu numar analize in catalog."""
    return get_laboratoare()


@router.get("/laboratoare/{laborator_id}/analize")
async def catalog_laborator(laborator_id: int, current_user: dict = Depends(get_current_user)):
    """Catalog analize pentru un laborator."""
    return get_laborator_analize(laborator_id)
