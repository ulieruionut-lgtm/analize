import json
import logging
import os
from typing import Dict, List, Optional

_log = logging.getLogger(__name__)


def _get_openai_client():
    """Returneaza client OpenAI (openai>=1.0). Ridica ImportError/EnvironmentError daca nu e disponibil."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "Instaleaza 'openai' pentru functii LLM: pip install \"openai>=1.0,<2.0\""
        )

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_3")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY nu este setat in environment.")

    return OpenAI(api_key=api_key)


def suggest_alias_from_llm(
    denumire_raw: str, snippets: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """Returneaza sugestii de alias din LLM pentru denumire necunoscuta.

    Returneaza lista de dict-uri cu cheile 'analiza_standard' si 'score'.
    Returneaza [] daca LLM nu e disponibil sau apelul esueaza.
    """
    if not denumire_raw or len(denumire_raw.strip()) < 3:
        return []

    try:
        client = _get_openai_client()
    except Exception as e:
        _log.warning("LLM unavailable: %s", e)
        return []

    prompt = (
        "Esti un parser medical pentru analize de laborator. "
        "Primesti o denumire extrasa dintr-un buletin de analize si returneaza o lista scurta "
        "de sugestii de analiza standard. "
        "Raspunde DOAR cu JSON valid, format: "
        "{\"candidates\": [{\"name\": \"Hemoglobina\", \"score\": 95}, ...]}\n"
        f"Denumire: '{denumire_raw.strip()}'\n"
    )
    if snippets:
        prompt += "Context valori: " + ", ".join(snippets[:5]) + "\n"

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful medical lab parser assistant. Respond only with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=250,
        )
        text = (resp.choices[0].message.content or "").strip()

        # Extrage JSON din raspuns (poate fi infasurat in markdown ```json ... ```)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []

        parsed = json.loads(text[start: end + 1])
        candidates = parsed.get("candidates") or parsed.get("suggestions") or []
        if not isinstance(candidates, list):
            return []

        result = []
        for item in candidates[:5]:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or item.get("label") or item.get("candidate") or "").strip()
            if not name:
                continue
            result.append({
                "analiza_standard": name,
                "score": float(item.get("score") or 0),
            })
        return result

    except Exception as exc:
        _log.warning("LLM suggestion failed for '%s': %s", denumire_raw, exc)
        return []
