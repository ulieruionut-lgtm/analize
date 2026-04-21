"""
Fragmente administrative / tipărire — sursă unică pentru filtre „gunoi”,
complementar cu regex-ul compus `_LINII_EXCLUSE` din parser.

Folosit de `_linie_este_exclusa` și `este_denumire_gunoi` ca să nu duplicăm
aceleași concepte în zeci de alternative regex.
"""
import re
import unicodedata
from typing import FrozenSet

# Subșiruri pe text normalizat (lowercase ASCII, spații colapsate)
FRAGMENTE_ADMINISTRATIVE_NORMALIZATE: FrozenSet[str] = frozenset(
    {
        "cod paraf",
        "cod parafa",
        "cod formular",
        "data tipar",
        "data tiparii",
        "data tiparirii",
        "analize rezultate interval",
        "interval biologic",
        "biologic de referin",
        "referinta / um",
        "referinta/ um",
        "referinta /um",
        # Note clinică / antet tabel (nu analize de laborator)
        "observatii",
        "observatie",
        "rezultatul se interpret",
        "interpretare in context clinic",
        "interpretare in contextul clinic",
        "in context clinic",
        # Vârstă scurtă tip footer OCR
        "ani, 3 luni",
        "ani 3 luni",
        "luni 3 ani",
        # Fragmente recurente in PDF-uri OCR unde se salveaza "gunoi" ca analize
        "tiparit de",
        "punct recolta",
        "punct de recoltare",
        "proba conforma",
        "proba:",
        "cod proba",
        "cod client",
        "data inregistrarii",
        "data rezultatului",
        "diagnostic",
        "adresa jud",
        "valori in afara limitelor admise",
        "opiniile si interpretarile",
        "aceste rezultate pot fi folosite",
        "analize subcontractate",
        "act zv",
        "medic trimitator",
        "cod document",
        "examen complet de urina",
        "valvulara mecanica",
        "god proba",
        "denumiretest",
        "tipareste",
        "foarte crescut",
        "proba numarul",
        "medicina de laborato",
        # TEO HEALTH / Spitalul Sf. Constantin Brasov
        "lucrat de",
        "validat de",
        "verificat dr",
        "verificat, dr",
        "medic sef laborato",
        "receptionat de",
        "data eliberarii",
        "data recoltarii",
        "data receptiei",
        "cod cerere analize",
        "buletin de analize",
        "cod cerere",
        "interval biologic de referinta",
        "nr denumire test rezultat",
        "nr. denumire test",
        "spitalul sf constantin",
        "spitalul sf. constantin",
        "teo health",
        "laborator analize medicale",
        "sr en iso",
        "certificat de acreditare",
        "scanati pentru",
        "vizualizare buletin",
        "pagina din",
        "ba 5",  # BA 52604 / BA 52608 etc — coduri buletin
        "analize neacreditate renar",
        "opiniile si interpretarile continute",
        "testele cu marcajul",
        "aceste rezultate pot fi",
        "cod document pgl",
    }
)


def _normalizeaza_pentru_fragmente(text: str) -> str:
    s = (text or "").strip().lower()
    s = s.replace("ș", "s").replace("ş", "s")
    s = s.replace("ț", "t").replace("ţ", "t")
    s = s.replace("ă", "a").replace("â", "a").replace("î", "i")
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    # OCR-ul introduce des simboluri/paraziti intre cuvinte; ii transformam in spatii
    # pentru matching robust al fragmentelor administrative.
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def contin_fragment_administrativ(text: str) -> bool:
    """True dacă textul conține un fragment administrativ cunoscut (oriunde în linie)."""
    if not text or not str(text).strip():
        return False
    n = _normalizeaza_pentru_fragmente(text)
    return any(frag in n for frag in FRAGMENTE_ADMINISTRATIVE_NORMALIZATE)
