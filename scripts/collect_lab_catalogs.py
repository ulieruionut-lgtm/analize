"""
Colecteaza catalogul de analize de la laboratoare din Romania.
Export JSON: { "laborator": "...", "analize": ["...", ...] }

Ruleaza: python scripts/collect_lab_catalogs.py
Output: data/lab_catalogs_*.json
"""
import json
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instaleaza: pip install requests")
    exit(1)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("(Optional) pip install beautifulsoup4 pentru parsare mai buna")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109) Gecko/20100101 Firefox/119",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ro,en-US;q=0.7,en;q=0.3",
}


def fetch_url(url: str, delay: float = 1.0) -> str | None:
    """Fetch URL cu rate limiting."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        time.sleep(delay)
        return r.text
    except Exception as e:
        print(f"  Eroare {url}: {e}")
        return None


def extract_analize_bioclinica(html: str) -> list[str]:
    """Extrage denumiri analize din pagina Bioclinica."""
    analize = []
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=re.compile(r"/analize/|/servicii/")):
            t = (a.get_text() or "").strip()
            if len(t) >= 3 and len(t) < 100 and t not in analize:
                if not re.match(r"^(Contact|Vezi|Detalii|Program)", t, re.I):
                    analize.append(t)
    else:
        for m in re.finditer(r'href="[^"]*analize[^"]*"[^>]*>([^<]{3,80})</a>', html):
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            if t and t not in analize:
                analize.append(t)
    return analize[:500]  # limit


def extract_analize_generic(html: str) -> list[str]:
    """Extrage potentiale denumiri analize din text (euristic)."""
    analize = []
    # Pattern: titluri sau linkuri cu denumiri medicale (2-60 caractere)
    words = ("hemoglobina", "glicemie", "creatinina", "leucocite", "colesterol",
             "tsh", "hdl", "ldl", "hematii", "trombocite", "feritina")
    for m in re.finditer(r">([^<]{4,70})<", html):
        t = m.group(1).strip()
        if any(w in t.lower() for w in words) or re.match(r"^[A-Z][a-zăâîșț]+(?:\s+[a-zăâîșț]+)*\s*[\d.]*$", t):
            if t not in analize and len(analize) < 200:
                analize.append(t)
    return analize


def collect_bioclinica() -> dict:
    """Colecteaza de la Bioclinica."""
    print("Bioclinica...")
    url = "https://bioclinica.ro/analize/biochimie"
    html = fetch_url(url)
    if not html:
        return {"laborator": "Bioclinica", "analize": []}
    analize = extract_analize_bioclinica(html)
    # Fallback: analize standard din 002
    if len(analize) < 20:
        analize = ["Hematii", "Hemoglobină", "Hematocrit", "Leucocite", "Trombocite",
                   "Glicemie", "Creatinină", "TGO (ASAT)", "TGP (ALAT)", "CRP",
                   "Colesterol total", "HDL", "LDL", "TSH", "Feritina"]
    return {"laborator": "Bioclinica", "website": "https://bioclinica.ro", "analize": analize}


def collect_synevo() -> dict:
    """Colecteaza de la Synevo (structura cunoscuta)."""
    print("Synevo...")
    url = "https://www.synevo.ro/analize-de-sange/"
    html = fetch_url(url)
    if not html:
        return {"laborator": "Synevo", "analize": []}
    analize = extract_analize_generic(html)
    if len(analize) < 10:
        analize = ["Hemoleucograma", "Glicemie", "Creatinina", "Colesterol total",
                   "TSH", "HbA1c", "Proteina C reactiva", "Eritrocite", "Leucocite"]
    return {"laborator": "Synevo", "website": "https://www.synevo.ro", "analize": analize}


def main():
    results = []
    for fn in [collect_bioclinica, collect_synevo]:
        try:
            data = fn()
            results.append(data)
            print(f"  -> {len(data.get('analize', []))} analize")
        except Exception as e:
            print(f"  Eroare: {e}")
    out = DATA_DIR / "lab_catalogs_collected.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nScris: {out}")


if __name__ == "__main__":
    main()
