"""Router analize: standard, necunoscute, alias-uri, rezultate, historicul."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend.database import (
    _row_get,
    _use_sqlite,
    add_rezultat_manual,
    adauga_analiza_standard,
    delete_rezultat_single,
    get_all_analize_standard,
    get_analize_necunoscute,
    get_cursor,
    get_historicul_analiza,
    get_necunoscute_by_ids,
    get_rezultate_buletin,
    goleste_analize_asociate,
    sterge_analiza_necunoscuta,
    update_rezultat,
)
from backend.deps import get_current_user
from backend.llm_chat import llm_provider_normalized, suggest_alias_llm_configured
from backend.llm_helper import sugestii_necunoscuta_cu_catalog
from backend.models import (
    AdaugaAnalizaStdBody,
    AdaugaRezultatBody,
    AprobaAliasBody,
    AprobaAliasBulkBody,
    SugestiiLlmNecunoscuteBody,
)

router = APIRouter()


@router.get("/analize-standard")
async def lista_analize_standard(current_user: dict = Depends(get_current_user)):
    """Lista tuturor tipurilor de analize din baza de date."""
    return get_all_analize_standard()


@router.post("/analize-standard")
async def adauga_analiza_std(body: AdaugaAnalizaStdBody, current_user: dict = Depends(get_current_user)):
    """Adauga o noua analiza standard (denumire + cod unic)."""
    denumire = body.denumire.strip()
    cod = body.cod.strip()
    if not denumire or not cod:
        raise HTTPException(status_code=400, detail="Denumirea si codul sunt obligatorii.")
    try:
        analiza = adauga_analiza_standard(denumire, cod)
        return analiza
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/buletin/{buletin_id}/rezultate")
async def get_buletin_rezultate(buletin_id: int, current_user: dict = Depends(get_current_user)):
    """Lista tuturor rezultatelor dintr-un buletin (pentru editare manuala)."""
    return get_rezultate_buletin(buletin_id)


@router.put("/rezultat/{rezultat_id}")
async def edit_rezultat(rezultat_id: int, body: dict, current_user: dict = Depends(get_current_user)):
    """Editeaza partial un rezultat existent. Daca se schimba analiza_standard_id, salveaza alias."""
    if not body:
        raise HTTPException(status_code=422, detail="Body gol — nimic de actualizat.")
    ok = update_rezultat(rezultat_id=rezultat_id, body=body)
    if not ok:
        raise HTTPException(status_code=404, detail="Rezultatul nu a fost gasit.")

    alias_salvat = False
    new_std_id = body.get("analiza_standard_id")
    if new_std_id:
        with get_cursor(commit=False) as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"SELECT denumire_raw FROM rezultate_analize WHERE id = {ph}", (rezultat_id,))
            row = cur.fetchone()
            if row:
                denumire = _row_get(row, 0 if _use_sqlite() else "denumire_raw")
                if denumire and denumire.strip():
                    from backend.normalizer import adauga_alias_nou
                    alias_salvat = adauga_alias_nou(denumire.strip(), int(new_std_id))

    return {"ok": True, "alias_salvat": alias_salvat}


@router.delete("/rezultat/{rezultat_id}")
async def sterge_rezultat(rezultat_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un singur rezultat dintr-un buletin."""
    ok = delete_rezultat_single(rezultat_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Rezultatul nu a fost gasit.")
    return {"ok": True}


@router.post("/buletin/{buletin_id}/rezultat")
async def adauga_rezultat(
    buletin_id: int,
    body: AdaugaRezultatBody,
    current_user: dict = Depends(get_current_user),
):
    """Adauga manual un rezultat intr-un buletin existent."""
    denumire = body.denumire_raw.strip()
    analiza_standard_id = body.analiza_standard_id
    row = add_rezultat_manual(
        buletin_id=buletin_id,
        analiza_standard_id=analiza_standard_id,
        denumire_raw=denumire,
        valoare=float(body.valoare),
        unitate=body.unitate,
        flag=body.flag,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Eroare la adaugarea rezultatului.")

    alias_salvat = False
    if analiza_standard_id and denumire:
        from backend.normalizer import adauga_alias_nou
        alias_salvat = adauga_alias_nou(denumire, int(analiza_standard_id))

    return {"ok": True, "id": row["id"], "alias_salvat": alias_salvat}


@router.get("/analize-necunoscute")
async def lista_necunoscute(toate: bool = False, current_user: dict = Depends(get_current_user)):
    """Analize nerecunoscute de normalizer (neaprobate sau toate)."""
    return get_analize_necunoscute(doar_neaprobate=not toate)


@router.post("/analize-necunoscute/sugestii-llm")
async def sugestii_llm_necunoscute(
    body: SugestiiLlmNecunoscuteBody,
    current_user: dict = Depends(get_current_user),
):
    """
    Sugestii de mapare la analiza_standard (LLM + fuzzy pe catalog).
    Necesita ANTHROPIC_API_KEY sau chei OpenAI-compat + LLM_PROVIDER.
    """
    if not suggest_alias_llm_configured():
        return {
            "ok": False,
            "llm_disponibil": False,
            "mesaj": "Configurează LLM: ANTHROPIC_API_KEY (recomandat) + LLM_PROVIDER=anthropic, sau chei OpenAI-compat.",
            "provider": llm_provider_normalized(),
            "items": [],
            "procesate": 0,
        }

    std = get_all_analize_standard()
    nec = get_analize_necunoscute(doar_neaprobate=True)
    if body.ids:
        want = {int(x) for x in body.ids}
        nec = [n for n in nec if n.get("id") in want]
    nec = nec[: body.limit]

    loop = asyncio.get_event_loop()
    items = []

    def _one_row(nrow: dict) -> dict:
        den = (nrow.get("denumire_raw") or "").strip()
        cat = (nrow.get("categorie") or "").strip() or None
        nid = nrow.get("id")
        try:
            sug = sugestii_necunoscuta_cu_catalog(den, std, categorie_pdf=cat)
            return {"id": nid, "denumire_raw": den, "sugestii": sug, "eroare": None}
        except Exception as exc:
            return {"id": nid, "denumire_raw": den, "sugestii": [], "eroare": str(exc)[:200]}

    for n in nec:
        item = await loop.run_in_executor(None, _one_row, n)
        items.append(item)

    cu_sugestii = sum(1 for it in items if it.get("sugestii"))

    return {
        "ok": True,
        "llm_disponibil": True,
        "mesaj": None,
        "provider": llm_provider_normalized(),
        "items": items,
        "procesate": len(items),
        "randuri_cu_sugestii": cu_sugestii,
    }


@router.post("/aproba-alias")
async def aproba_alias(body: AprobaAliasBody, current_user: dict = Depends(get_current_user)):
    """Asociaza o denumire_raw necunoscuta cu o analiza_standard."""
    aid = body.analiza_standard_id
    raw = (body.denumire_raw or "").strip()
    nid = body.necunoscuta_id
    if nid is not None:
        rows = get_necunoscute_by_ids([nid])
        if not rows:
            return JSONResponse(
                status_code=404,
                content={"detail": "Intrarea nu există sau este deja aprobată."},
            )
        raw = (rows[0].get("denumire_raw") or "").strip()
    if not raw or not aid:
        return JSONResponse(
            status_code=400,
            content={"detail": "Campuri obligatorii: analiza_standard_id și (denumire_raw sau necunoscuta_id)."},
        )
    from backend.normalizer import adauga_alias_nou
    ok = adauga_alias_nou(raw, int(aid))
    if ok:
        return {"ok": True, "mesaj": f"Alias '{raw}' asociat cu succes."}
    return JSONResponse(status_code=500, content={"detail": "Eroare la salvarea alias-ului."})


@router.post("/aproba-alias-bulk")
async def aproba_alias_bulk(body: AprobaAliasBulkBody, current_user: dict = Depends(get_current_user)):
    """Aprobare in masa: aceeasi analiza standard pentru mai multe randuri din analiza_necunoscuta."""
    ids = body.necunoscuta_ids or body.ids or []
    aid_int = body.analiza_standard_id
    if not isinstance(ids, list) or not ids:
        return JSONResponse(status_code=400, content={"detail": "Lista necunoscuta_ids este goală sau invalidă."})

    rows = get_necunoscute_by_ids(ids)
    if not rows:
        return JSONResponse(status_code=404, content={"detail": "Nicio intrare neaprobată găsită pentru id-urile date."})

    requested = set()
    for x in ids:
        try:
            requested.add(int(x))
        except (TypeError, ValueError):
            pass
    found_ids = {r.get("id") for r in rows}
    skipped_ids = sorted(requested - found_ids)

    denumiri = [(r.get("denumire_raw") or "").strip() for r in rows]
    denumiri = [d for d in denumiri if d]
    if not denumiri:
        return JSONResponse(status_code=400, content={"detail": "Denumiri goale."})

    from backend.normalizer import adauga_aliasuri_bulk
    result = adauga_aliasuri_bulk(denumiri, aid_int)
    if not result.get("ok"):
        return JSONResponse(
            status_code=500,
            content={"detail": result.get("error") or "Eroare la aprobare în masă."},
        )
    return {
        "ok": True,
        "mesaj": f"Asociate {result.get('processed', 0)} denumiri la analiza standard {aid_int}.",
        "processed": result.get("processed", 0),
        "rows_matched": len(rows),
        "skipped_ids": skipped_ids,
    }


@router.post("/invalideaza-cache-alias")
async def invalideaza_cache_alias(current_user: dict = Depends(get_current_user)):
    """Invalideaza cache-ul alias-urilor (dupa aprobari bulk)."""
    from backend.normalizer import invalideaza_cache
    invalideaza_cache()
    return {"ok": True, "mesaj": "Cache alias invalidat."}


@router.post("/api/admin/auto-alias-necunoscute")
async def auto_alias_necunoscute(current_user: dict = Depends(get_current_user)):
    """
    Parcurge analiza_necunoscuta (neaprobate) si incearca auto-matching pe analiza_standard.
    Salveaza automat alias + actualizare retroactiva pentru match-urile cu scor suficient.
    """
    from backend.normalizer import auto_rezolva_necunoscute
    result = await asyncio.get_event_loop().run_in_executor(None, auto_rezolva_necunoscute)
    return result


@router.post("/goleste-analize-asociate")
async def goleste_asociate(current_user: dict = Depends(get_current_user)):
    """Sterge toate intrarile din analiza_necunoscuta si analiza_alias."""
    from backend.normalizer import invalideaza_cache
    result = goleste_analize_asociate()
    invalideaza_cache()
    return result


@router.delete("/analiza-necunoscuta/{id_nec}")
async def sterge_necunoscuta(id_nec: int, current_user: dict = Depends(get_current_user)):
    """Sterge o analiza necunoscuta (ex: zgomot, artefact OCR)."""
    sterge_analiza_necunoscuta(id_nec)
    return {"ok": True}


@router.get("/analiza-historicul/{analiza_id}")
async def historicul_analiza(analiza_id: int, current_user: dict = Depends(get_current_user)):
    """Toate rezultatele pentru un tip de analiza (dupa id), de la toti pacientii."""
    rezultate = get_historicul_analiza(analiza_id)
    return {"analiza_id": analiza_id, "rezultate": rezultate, "total": len(rezultate)}
