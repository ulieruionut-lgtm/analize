# -*- coding: utf-8 -*-
"""Extragere buletin de analize direct din imagini pagini PDF — Claude Vision (Anthropic).

Folosit ca fallback când OCR Tesseract produce text degradat/insuficient.
Trimite imaginile paginilor la Claude Vision și returnează date structurate.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

_VISION_SYSTEM = (
    "Ești un extractor medical specializat pe buletine de analize de laborator românești. "
    "Analizezi imagini de pagini dintr-un buletin și extragi structurat toate datele medicale. "
    "Răspunzi EXCLUSIV cu JSON valid, fără markdown, fără explicații suplimentare."
)

_VISION_USER = """\
Extrage din imaginile acestui buletin de analize medicale românesc:
1. Numele pacientului (câmpul Nume + Prenume)
2. CNP-ul pacientului (exact 13 cifre)
3. TOATE analizele cu valorile lor (nu omite niciuna)

Categorii posibile de analize: Hemoleucogramă, Biochimie, Lipidogramă, Hormoni tiroidieni, \
Hormoni, Examen urină, Sediment urinar, Microbiologie, Coagulare, Imunologie, \
Markeri tumorali, Inflamație

Răspunde DOAR cu JSON (absolut nimic altceva în afara JSON-ului):
{
  "pacient_nume": "POPESCU",
  "pacient_prenume": "ION",
  "cnp": "1234567890123",
  "analize": [
    {
      "denumire": "Colesterol total",
      "valoare": "297.89",
      "unitate": "mg/dL",
      "interval": "<200 mg/dL",
      "categorie": "Biochimie"
    }
  ]
}"""


def get_pages_as_image_bytes(pdf_path: str, dpi: int = 150) -> List[bytes]:
    """Redă fiecare pagină PDF ca bytes PNG — pentru Claude Vision."""
    try:
        import fitz  # PyMuPDF

        pages: List[bytes] = []
        doc = fitz.open(pdf_path)
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for page in doc:
            try:
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                pages.append(pix.tobytes("png"))
            except Exception:
                continue
        doc.close()
        return pages
    except Exception as exc:
        _log.warning("get_pages_as_image_bytes failed: %s", exc)
        return []


def _is_vision_available() -> bool:
    """Returnează True dacă Anthropic Vision e configurată (cheie API + sdk)."""
    try:
        from backend.llm_chat import _anthropic_api_key

        return bool(_anthropic_api_key())
    except Exception:
        return False


def extract_buletin_with_vision(
    page_images: List[bytes],
    *,
    timeout: float = 120.0,
) -> Optional[Dict[str, Any]]:
    """
    Trimite imaginile paginilor PDF la Claude Vision și returnează datele extrase ca dict.
    Returnează None dacă extracția eșuează sau Anthropic nu e configurat.
    """
    if not page_images:
        return None

    try:
        from backend.llm_chat import _anthropic_api_key

        key = _anthropic_api_key()
        if not key:
            _log.debug("Vision extraction: lipsește ANTHROPIC_API_KEY")
            return None
        import anthropic
    except (ImportError, Exception) as exc:
        _log.warning("Vision extraction indisponibilă: %s", exc)
        return None

    # Vision folosește întotdeauna Anthropic; dacă provider-ul configurat e OpenAI,
    # folosim haiku (vision-capable, rapid, cost redus).
    from backend.llm_chat import llm_provider_normalized
    configured_model = resolve_model_name()
    if llm_provider_normalized() == "anthropic" and configured_model:
        vision_model = configured_model
    else:
        vision_model = "claude-haiku-4-5"

    content: List[Dict[str, Any]] = []
    for img_bytes in page_images[:6]:  # max 6 pagini
        b64 = base64.standard_b64encode(img_bytes).decode("ascii")
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            }
        )
    content.append({"type": "text", "text": _VISION_USER})

    try:
        client = anthropic.Anthropic(api_key=key, timeout=timeout)
        msg = client.messages.create(
            model=vision_model,
            max_tokens=4096,
            system=_VISION_SYSTEM,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
        )
        raw = ""
        for block in msg.content:
            if getattr(block, "text", None):
                raw += block.text
            elif isinstance(block, dict) and block.get("type") == "text":
                raw += str(block.get("text") or "")
        raw = raw.strip()
        # Strip eventual markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```\s*$", "", raw)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            _log.warning("Vision extraction: răspuns fără JSON valid")
            return None
        return json.loads(raw[start : end + 1])
    except Exception as exc:
        _log.warning("Vision extraction eșuată: %s", exc)
        return None


def vision_data_to_patient_parsed(data: Dict[str, Any]):
    """Convertește JSON Vision în PatientParsed cu RezultatParsat pentru fiecare analiză."""
    from backend.models import PatientParsed, RezultatParsat

    nume = (data.get("pacient_nume") or "Necunoscut").strip() or "Necunoscut"
    prenume = (data.get("pacient_prenume") or "").strip() or None
    cnp_raw = re.sub(r"\D", "", str(data.get("cnp") or ""))
    cnp = cnp_raw if len(cnp_raw) == 13 else "0000000000000"

    rezultate: List[RezultatParsat] = []
    for i, analiza in enumerate(data.get("analize") or []):
        den = (analiza.get("denumire") or "").strip()
        if not den or len(den) < 2:
            continue

        val_raw = analiza.get("valoare")
        val_num: Optional[float] = None
        val_text: Optional[str] = None
        if val_raw is not None:
            s = str(val_raw).strip().replace(",", ".")
            s_clean = re.sub(r"^[<>≥≤]=?\s*", "", s)
            try:
                val_num = float(s_clean)
            except (ValueError, TypeError):
                val_text = str(val_raw).strip() or None

        unit = (analiza.get("unitate") or "").strip() or None
        cat = (analiza.get("categorie") or "").strip() or None
        interval_raw = (analiza.get("interval") or "").strip()
        int_min: Optional[float] = None
        int_max: Optional[float] = None
        if interval_raw:
            m = re.match(r"<\s*(\d+(?:[.,]\d+)?)", interval_raw)
            if m:
                try:
                    int_max = float(m.group(1).replace(",", "."))
                except ValueError:
                    pass
            else:
                m2 = re.match(r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)", interval_raw)
                if m2:
                    try:
                        int_min = float(m2.group(1).replace(",", "."))
                        int_max = float(m2.group(2).replace(",", "."))
                    except ValueError:
                        pass
                else:
                    m3 = re.match(r">\s*(\d+(?:[.,]\d+)?)", interval_raw)
                    if m3:
                        try:
                            int_min = float(m3.group(1).replace(",", "."))
                        except ValueError:
                            pass

        rezultate.append(
            RezultatParsat(
                denumire_raw=den,
                valoare=val_num,
                valoare_text=val_text,
                unitate=unit,
                interval_min=int_min,
                interval_max=int_max,
                categorie=cat,
                ordine=i,
            )
        )

    return PatientParsed(cnp=cnp, nume=nume, prenume=prenume, rezultate=rezultate)


def try_vision_fallback(
    tmp_path: str,
    parsed_ocr,
    *,
    tip: str,
    upload_warnings: List[str],
) -> tuple:
    """
    Dacă OCR a produs rezultate slabe (nume necunoscut sau <8 analize),
    încearcă extracția cu Claude Vision și returnează (parsed, extractor_suffix).

    Dacă Vision nu îmbunătățește rezultatele sau nu e disponibilă, returnează (parsed_ocr, "").
    """
    if tip not in ("ocr", "text"):
        return parsed_ocr, ""

    name_ok = (parsed_ocr.nume or "").strip().lower() not in ("necunoscut", "", "0")
    count_ocr = len(parsed_ocr.rezultate)

    # Nu e nevoie de Vision dacă avem deja un nume și suficiente analize
    if name_ok and count_ocr >= 8:
        return parsed_ocr, ""

    if not _is_vision_available():
        return parsed_ocr, ""

    try:
        page_images = get_pages_as_image_bytes(tmp_path)
        if not page_images:
            return parsed_ocr, ""

        vision_data = extract_buletin_with_vision(page_images)
        if not vision_data:
            return parsed_ocr, ""

        parsed_vision = vision_data_to_patient_parsed(vision_data)
        count_vision = len(parsed_vision.rezultate)

        vision_name_ok = (parsed_vision.nume or "").strip().lower() not in ("necunoscut", "", "0")
        vision_better = (count_vision > count_ocr) or (vision_name_ok and not name_ok)

        if not vision_better:
            return parsed_ocr, ""

        # Preia CNP din OCR dacă Vision nu l-a găsit (OCR citește text nativ mai bine)
        if parsed_vision.cnp in ("0000000000000", "", None) and parsed_ocr.cnp not in ("0000000000000", "", None):
            parsed_vision.cnp = parsed_ocr.cnp

        upload_warnings.append(
            f"OCR a găsit {count_ocr} analize (calitate scăzută). "
            f"AI Vision a extras {count_vision} analize cu denumiri corecte."
        )
        _log.info(
            "Vision fallback: OCR=%d analize → Vision=%d analize, name=%r",
            count_ocr,
            count_vision,
            parsed_vision.nume,
        )
        return parsed_vision, "+vision"

    except Exception as exc:
        _log.warning("try_vision_fallback error: %s", exc)
        return parsed_ocr, ""
