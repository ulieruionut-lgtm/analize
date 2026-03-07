"""Extragere CNP (cu validare), Nume si rezultate analize din text.
Suporta formatele:
 - Bioclinica: parametru pe o linie, valoare + unitate + (interval) pe linia urmatoare
 - MedLife si formate similare: tot pe o linie - Parametru  Valoare  UM  Min-Max UM
"""
import re
from typing import Optional

from backend.models import PatientParsed, RezultatParsat

CNP_CONTROL = (2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9)

# Linii care NU sunt parametri medicali
_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"Reproducerea|Pentru|Nu se|Este|Valori|Opiniile|Analizele|Se utilizeaz|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|18\.02\.|29\.05\.|"
    r"brasov@|RENAR|seria|serie|Nr\.\s+\d|Buletin de analize|Data tipar|"
    r"Test Rezultat|Hematologie|Electroforeza|Validat|Verificat|PORUMBOI|"
    r"MEDIC |COD:|Sange |Ser,|Ser\.|Intr-un|Probele|Se interzice|Registrul|"
    r"Activitate|Analize neacreditate|Opinii|Rezultatele examinarilor|"
    r"Probele biologice|acreditat|Policlinica|Laborator de|eMail|Corp Central|"
    r"Aripa de|Jud\.|Loc\.|Telefon program|Punct recoltare|Adresa:|Telefon:|"
    r"Cod client|Cod proba|Cod caz|Varsta|Sex:|Prenume:|Nume:|Medic:|Cabinet|"
    # Antete sectiuni laborator
    r"HEMOLEUCOGRAMA|BIOCHIMIE|IMUNOLOGIE|HORMONI|SUMAR URINA|COAGULARE|"
    r"LIPIDOGRAMA|ELECTROFOREZA|SEROLOGIE|MARKERI|MINERALE|"
    # Note de clasificare (ex: "Crescut : 160-189", "Acceptabil: < 110")
    r"Acceptabil\s*:|Borderline|Crescut\s*[:\(]|Foarte\s+crescut|"
    r"Usor\s+crescut|Moderat\s+crescut|crescute?\s*[>:]|"
    r"Normal\s*:|Optim\s*:|Risc\s*:|Deficit\s+|Nivel\s+toxic|"
    # Note cu varsta/trimestru
    r"\d{1,3}-\d{1,3}\s+ani|peste\s+\d+\s+ani|trimest|"
    r"persoanelor|persoane\s+varst|"
    # Note diagnostice
    r"Diagnosticul|Glicemie\s+bazala\s+modif|Se\s+recomanda\s+retest|"
    # Artefacte OCR si certificate
    r"Regulamentul\s+nr|CERTIFICAT|certificat|Seria\s+[A-Z]|Nr\.\s+[A-Z]|"
    # Linii administrative laborator
    r"Cod\s+Cerere|Cod\s+Proba|Formular:|Act:\s+[A-Z]|Cont:\s+RO|"
    r"uz\s+personal|executate\s+de\s+parteneri|ghidului\s+KDIGO|"
    r"Data\s+nasterii|Spectrofotome|CITOMETRIE|Raspuns\s+rapid|"
    r"amoxicillin|Cefuroxime|diabet\s+zaharat|"
    r"Bacteriurie\s*[:(]|Leucociturie\s*[:(]|"
    r"RETEAUA\s+PRIVATA|RETEA\s+PRIVAT|Regina\s+Maria|REGINA\s+MARIA|"
    r"Punct\s+de\s+lucru|Cod\s+de\s+bare|Cod:|Coad:|PD\s+\d|"
    r"Data\s+-\s+ora\s+recolt|ora\s+recoltare|Data\s+recoltare|"
    # Intervale referinta si clasificari
    r"Usor\s+crescut|Moderat\s+crescut|Foarte\s+crescut|"
    r"Optim\s*:|Normal\s*:|Diabet\s+|Glicemie\s+bazala|"
    r"trimestrul|trimester\s+[I]|20-40\s+ani|peste\s+40\s+ani|"
    r"eGFR:\s*[<>]|G1\s+=|G2\s+=|G3|G4|G5|"
    r"eGFR:\s*\d|eGFR:\s*\d{2,}|eGFR:\s*[≥≤]|"
    # Linii de clasificare CKD/eGFR cu numar (ex: "eGFR: 2", "eGFR: 60 -")
    r"eGFR:\s*\d+\s*[-–]?|"
    # Linii de interpretare cu valori inglobate (format: ANALIZA valoare UM <comparator interp)
    # ex: "HDL COLESTEROL 68.2 mg/dL > 60 enma V", "TRIGLICERIDE 112 mg/dL <150 ME)"
    r"Scazut\s*\(risc|risc\s+scazut|risc\s+crescut|risc\s+moderat|"
    r"Interpretare\s+valori|Interpretare\s+rezultat|"
    r"posibil\s+deficit|posibila\s+intol|incidenta\s+scazuta|"
    r"intoleranta\s+la\s+histamina|"
    r"3-10\s+U/ml|U/ml\s+posibila|U/ml\s+intoleranta|"
    r"<\s*\d+\s*U/ml|>\s*\d+\s*U/ml|"
    # Note explicative lungi (>80 chars cu cuvinte comune)
    r"testare\s+corecta|obligatoriu\s+pe\s+nemancate|absenta\s+oricarei|"
    r"medicatii\s+\(clasice|clasice\s+sau\s+naturiste|"
    # Linii administrative Regina Maria / alte lab
    r"REȚEAUA\s+PRIVATĂ|SĂNĂTATE\s+Data|Data\s+-\s+ora|"
    r"MICROBIOLOGIE|UROCULTURA|"
    # Footer/disclaimer Regina Maria (OCR: BOBEICA, BCBEIEZA = nume medic)
    r"BOBEICA|BCBEIEZA|Testele cu marcajul\s+\*\*|Aceste rezultate pot fi folosite|"
    r"doza\s+\(0\.5\s+g\s+amoxicillin|A1\s+<\s*30:\s*albuminurie|"
    # Gunoi OCR: linii care incep cu 1-2 litere + spatiu + numar (ex: "ti = 7", "Li = 7")
    r"^(ti|Li)\s+[=:]?\s*\d|"
    # Footer/disclaimer Regina Maria (nume medic + "Testele cu marcajul", "Pagina X din")
    r"BOBEICA\s+ANA|BCBEIEZA\s+ANA|Testele\s+cu\s+marcajul|"
    r"Aceste\s+rezultate\s+pot\s+fi\s+folosite\s+pentru\s+uz\s+personal|"
    r"doza\s+\(0\.5\s+g\s+amoxicillin|"
    r"A1\s+<\s*30\s*:\s*albuminurie|"
    # Organisme urocultura "X spp -" (absent) - fragment tabel, nu parametru
    r"Enterococcus\s+spp\s+-|Streptococcus\s+spp\s+-|Staphylococcus\s+spp\s+-|"
    r"Pseudomonas\s+spp\s+-|Enterobacteriaceae\s+-|Candida\s+spp\s+-|"
    r"micologic.*antibiograma.*Streptococ|nevoie\s+Candida\s+spp|"
    # Gunoi OCR scurt (1-2 litere) si organisme urocultura
    r"^\s*ti\s*$|^\s*Li\s*$|Enterococcus\s+spp\s+-|Streptococcus\s+spp\s+-|"
    r"Staphylococcus\s+spp\s+-|Pseudomonas\s+spp\s+-|Enterobacteriaceae\s+-|"
    # Linii scurte care incep cu punct/doua puncte/spatiu (artefacte tabele)
    r":\s*[a-z]\s+[a-z]|^\s*[:\.\-]\s|"
    # Linii care incep cu ghilimele tipografice OCR sau simboluri speciale
    r"^[\u201e\u201c\u201d\u00ab\u00bb\*\#\~\^\|\\\/]+|"
    # Linii de interpretare cu valoare+UM+comparator inglobate
    # ex: "HDL COLESTEROL 68.2 mg/dL > 60 enma V", "TRIGLICERIDE 112 mg/dL <150 ME)"
    # ex: "FOLATI SERICI 7.64 ng/mL >5.38 De A", "crescute 2 126.0 mg/dl"
    r"crescute?\s+\d|Normal\s*[:<>]\s*\d|Optim\s*[:<>]\s*\d)",
    re.IGNORECASE,
)

_LINIE_NOTA = re.compile(r"^\(|^\s*\(")

# ─── Recunoastere sectiuni (categorii) din buletine ──────────────────────────
# Mapare: pattern regex -> denumire categorie normalizata
_SECTIUNI = [
    (re.compile(r"HEMATOLOGIE|HEMOLEUCOGRAMA|FORMULA\s+LEUCOCITAR|HEMOGRAM", re.IGNORECASE),
     "Hemoleucograma"),
    (re.compile(r"BIOCHIMIE\s+URIN|EXAMEN\s+COMPLET\s+DE\s+URIN|SUMAR\s+URIN|SUMAR\s+SI\s+SEDIMENT|SEDIMENT\s+URINAR|BIOCHIMIE\s*URINA|URIN[AĂ]", re.IGNORECASE),
     "Examen urina"),
    (re.compile(r"BIOCHIMIE|BIOCHIMIA|BIOCHIM", re.IGNORECASE),
     "Biochimie"),
    (re.compile(r"LIPIDOGRAM|PROFIL\s+LIPIDIC|LIPIDE", re.IGNORECASE),
     "Lipidograma"),
    (re.compile(r"ELECTROFOREZ", re.IGNORECASE),
     "Electroforeza"),
    (re.compile(r"IMUNOLOGIE\s+SI\s+SEROLOGIE|IMUNOLOGIE|SEROLOGIE", re.IGNORECASE),
     "Imunologie si Serologie"),
    (re.compile(r"HORMONI\s+TIROID|TIROID", re.IGNORECASE),
     "Hormoni tiroidieni"),
    (re.compile(r"HORMONI|ENDOCRIN", re.IGNORECASE),
     "Hormoni"),
    (re.compile(r"COAGULARE|HEMOSTAZ", re.IGNORECASE),
     "Coagulare"),
    (re.compile(r"MARKERI\s+TUMOR|ONCOLOGIC", re.IGNORECASE),
     "Markeri tumorali"),
    (re.compile(r"MINERALE|ELECTROLITI|OLIGOELEMENTE", re.IGNORECASE),
     "Minerale si electroliti"),
    (re.compile(r"INFLAMATIE|REACTANTI\s+DE\s+FAZ|VSH|CRP", re.IGNORECASE),
     "Inflamatie"),
    (re.compile(r"PROTEINA\s+C\s+REACTIV", re.IGNORECASE),
     "Inflamatie"),
    (re.compile(r"RAPORT\s+ALBUMIN|MICROALBUMIN", re.IGNORECASE),
     "Examen urina"),
]

def _detecteaza_sectiune(linie: str) -> Optional[str]:
    """Returneaza numele sectiunii daca linia este un antet de sectiune, altfel None."""
    linie = linie.strip()
    # Antetele de sectiune sunt de obicei scurte (< 80 chars) si fara valori numerice
    if not linie or len(linie) > 100:
        return None
    # Nu trebuie sa contina valori numerice (nu e un rezultat)
    if re.search(r"\d+[.,]\d+|\s\d+\s", linie):
        return None
    for pattern, categorie in _SECTIUNI:
        if pattern.search(linie):
            return categorie
    return None

# Valori text frecvente in analizele medicale (sumar urina, culturi, etc.)
_VALOARE_TEXT_RE = re.compile(
    r"^(negativ[ae]?|pozitiv[ae]?|absent[ae]?|prezent[ae]?|rar[ae]?|normal[ae]?|"
    r"crescut[ae]?|scazut[ae]?|reactiv[ae]?|nedecelabil[ae]?|nedetectabil[ae]?|"
    r"epitelii\s+\w+|leucocite\s+\w+|hematii\s+\w+|cilindri\s+\w+|"
    r"cristale\s+\w+|bacterii\s+\w+|mucus\s+\w+|"
    r"galben[ae]?|incolor[ae]?|tulbure|limpede|clar[ae]?|"
    r"urme|trace[s]?|uro\s*\d*|"
    r"[<>]\s*\d+[\.,]?\d*\s*\w*)",
    re.IGNORECASE,
)

# Format Bioclinica: valoare+unitate + interval in paranteza
RE_VALOARE_LINIE = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Format valoare simpla fara interval
RE_VALOARE_PARTIAL = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/m]+?)$",
    re.IGNORECASE,
)


def validare_cnp(cnp: str) -> bool:
    if not re.match(r"^[1-8]\d{12}$", cnp):
        return False
    s = sum(int(cnp[i]) * CNP_CONTROL[i] for i in range(12)) % 11
    if s == 10:
        s = 1
    return s == int(cnp[12])


def extract_cnp(text: str) -> Optional[str]:
    for m in re.finditer(r"\b[1-8]\d{12}\b", text):
        if validare_cnp(m.group()):
            return m.group()
    return None


# Cuvinte-cheie dupa care taiem (nu fac parte din numele pacientului)
_NUME_TAIERE = re.compile(
    r"\s+(?:Medic\s+trimitaro?r?|Medic|Data|Cabinet|Sex|Varsta|Cod|Adresa|Telefon|"
    r"Punctul|Punct|pacient\s*:|Pra\s+pacient|Beneficiar)\s*[:\s]",
    re.IGNORECASE,
)


def _curata_nume(raw: str) -> str:
    """Extrage doar numele din text care poate contine 'Medic trimitator:', 'Varsta:', etc."""
    if not raw or not raw.strip():
        return raw or ""
    s = raw.strip()
    # Taie la primul cuvant-cheie care nu face parte din nume
    parts = _NUME_TAIERE.split(s, maxsplit=1)
    s = parts[0].strip()
    # Curata artefacte OCR de la sfarsit
    s = re.sub(r"\s+[a-z]{1,2}\s*$", "", s).strip()
    s = re.sub(r"\s+[FM]\s*[|]\s*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*\|\s*$", "", s).strip()
    return s


def extract_nume(text: str) -> tuple[str, Optional[str]]:
    """
    Incearca mai intai formatele explicite 'Nume pacient:', 'Nume:' (MedLife, Synevo etc.).
    Dupa aceea cauta backward de la CNP (format Bioclinica).
    """
    # --- Varianta 1a: "Nume pacient:" (format cu eticheta completa) ---
    m_np = re.search(r"(?:^|\n)\s*Nume\s+pacient\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_np:
        raw_n = _curata_nume(m_np.group(1))
        if raw_n and len(raw_n) >= 2:
            parts = raw_n.split(None, 1)
            if len(parts) >= 2:
                return parts[0], parts[1]  # nume, prenume -> afisat "NUME PRENUME"
            return raw_n, None

    # --- Varianta 1b: "Nume:" (format scurt) ---
    m_n = re.search(r"(?:^|\n)\s*Nume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    m_p = re.search(r"(?:^|\n)\s*Prenume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_n:
        raw_n = _curata_nume(m_n.group(1))
        if not raw_n:
            raw_n = m_n.group(1).strip()  # fallback fara curatare
        prenume = None
        if m_p:
            raw_p = _curata_nume(m_p.group(1))
            raw_p = re.sub(r"\s+ol\s*$", "", raw_p or "", flags=re.IGNORECASE).strip()
            prenume = raw_p if raw_p else None
            if prenume and prenume != raw_n:
                return f"{raw_n} {prenume}".strip(), prenume
        return raw_n, prenume

    # --- Varianta 2: backward de la CNP (format Bioclinica) ---
    m_cnp = re.search(r"\bCNP\s*:?\s*[1-8]\d{12}\b", text)
    if m_cnp:
        before = text[:m_cnp.start()].strip()
        lines_before = [l.strip() for l in before.split("\n") if l.strip()]
        for linie in reversed(lines_before):
            if re.match(r"^[\d\(]", linie):
                continue
            if _LINII_EXCLUSE.match(linie):
                continue
            clean = re.sub(r"\s+[FM],\s*\d+\s*(luni|ani)\s*$", "", linie, flags=re.IGNORECASE).strip()
            clean = _curata_nume(clean)  # taie Medic trimitator, Varsta etc.
            if clean and re.search(r"\b[A-ZȘȚĂÂÎ]{2,}", clean):
                parts = clean.split(None, 1)
                return clean, parts[1] if len(parts) >= 2 else None

    # --- Varianta 3: fallback generic ---
    for pat in [r"(?:Pacient|Beneficiar)\s*[:\-]\s*([^\n]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = _curata_nume(m.group(1))
            if raw:
                parts = raw.split(None, 1)
                return raw, parts[1] if len(parts) >= 2 else None

    return "Necunoscut", None


def _este_gunoi_ocr(linie: str) -> bool:
    """
    Detecteaza linii de gunoi OCR: siruri de litere/silabe fara sens, separate prin spatii.
    Semne: mai mult de 40% din 'cuvinte' au sub 2 litere, sau linia are aspectul unui tabel
    OCR-izat prost (multe litere unice, silabe scurte, fara niciun cuvant medical real).
    """
    linie = linie.strip()
    if not linie:
        return False
    # Cuvinte reale de analize medicale — daca oricare apare, NU e gunoi
    _CUVINTE_MEDICALE = re.compile(
        r"\b(hemoglobin|eritrocit|leucocit|trombocit|hematocrit|neutrofil|limfocit|"
        r"monocit|eozinofi|bazofil|creatinin|glucoz|glicemi|colesterol|triglicerid|"
        r"bilirubina|feritina|fier|sodiu|potasiu|calciu|magneziu|fosfor|uree|acid|"
        r"proteina|albumin|globulin|fibrinogen|vitamina|hormon|tsh|t3|t4|cortizol|"
        r"insulina|hemoglo|plachetar|eritrocitar|seric|urinar|sediment|sumar|"
        r"homocistein|complement|anticorp|imunoglobul|DAO|VSH|CRP|ALT|AST|GGT)\b",
        re.IGNORECASE,
    )
    if _CUVINTE_MEDICALE.search(linie):
        return False
    # Imparte in cuvinte (secvente ne-spatiu)
    cuvinte = linie.split()
    if len(cuvinte) < 4:
        return False
    # Numara cuvintele scurte (1-2 litere)
    scurte = sum(1 for c in cuvinte if len(re.sub(r'[^a-zA-ZăâîșțĂÂÎȘȚ]', '', c)) <= 2)
    # Daca >55% sunt silabe scurte => gunoi OCR
    if scurte / len(cuvinte) > 0.55:
        return True
    # Daca linia contine secvente de litere unice separate prin spatiu (tabel degradat)
    # ex: "i CR CE SERE De E Oa nea" - mai mult de 5 litere unice consecutive
    litere_unice = re.findall(r'\b[a-zA-ZăâîșțĂÂÎȘȚ]\b', linie)
    if len(litere_unice) >= 5 and len(litere_unice) / len(cuvinte) > 0.4:
        return True
    return False


# Substring-uri care indica gunoi OCR / footer (Regina Maria etc.) - oriunde in linie
_GUNOI_SUBSTR = (
    "BOBEICA", "BCBEIEZA", "Testele cu marcajul", "Aceste rezultate pot fi folosite",
    "doza (0.5 g amoxicillin", "A1 <30: albuminurie", "Pagina ", " din ",
    " spp -", "Enterobacteriaceae -", "micologic", "antibiograma", "nevoie Candida",
    "in 05.01.2026", "in 06.01.2026", "in 22.12.2025",  # disclaimer cu data
)


def _este_linie_parametru(linie: str) -> bool:
    if not linie or len(linie) > 150:
        return False
    if _LINII_EXCLUSE.match(linie):
        return False
    # Footer/disclaimer - exclude oriunde in linie
    linie_upper = linie.upper()
    if any(g.upper() in linie_upper for g in _GUNOI_SUBSTR):
        return False
    if _LINIE_NOTA.match(linie):
        return False
    if re.search(r"\d{9,}", linie):
        return False
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", linie):
        return False
    # Linii care incep cu semne de punctuatie sau caractere speciale (artefacte tabele)
    if re.match(r'^["\'\[\]\{\}:;|\\]', linie):
        return False
    # Linii de clasificare/referinta: "Ceva: < 60", "eGFR: = 142", "k = 0.7"
    if re.search(r':\s*[<>=≤≥]\s*\d', linie):
        return False
    # Linii cu text foarte scurt si ambiguu (< 4 caractere utile)
    if len(re.sub(r'[^a-zA-Z]', '', linie)) < 3:
        return False
    # Detecteaza gunoi OCR (tabele degradate, siruri de silabe fara sens)
    if _este_gunoi_ocr(linie):
        return False
    # Linii care incep cu numar de linie (ex: "9.3 Alfa2-globuline%", "1. Hemoglobina")
    # dar NU linii care incep cu valori medicale cunoscute (ex: "25-OH Vitamina D")
    if re.match(r'^\d+\.\d+\s+[A-Z]', linie):
        # Sterge prefixul numeric si continua parsarea cu restul
        linie_fara_prefix = re.sub(r'^\d+\.\d+\s+\*?\s*', '', linie).strip()
        if linie_fara_prefix != linie:
            return _este_linie_parametru(linie_fara_prefix)
    return True


def _parse_oneline(linie: str) -> Optional[RezultatParsat]:
    """
    Parseaza o linie de forma:  NumeAnaliza  Valoare  UM  [Min-Max [UM]] [flag]
    Exemple:
      Hemoglobina 16.4 g/dL 13.0-17.0 g/dl
      Hematocrit 49.1 % 40-50%
      CRP cantitativ 187 mg/L 0-5 mgii
      RDW-CV 144 % 11.5-145%
    """
    linie = linie.strip()
    if not linie:
        return None

    # Elimina prefix numeric de linie (ex: "9.3 Alfa2-globuline%" -> "Alfa2-globuline%")
    linie = re.sub(r'^\d+\.\d+\s+\*?\s*', '', linie).strip()
    if not linie:
        return None

    # Detecteaza valoarea reala inglobata in paranteze patrate in denumire
    # ex: "CALCIU SERIC [10.66 mg/dL]" -> valoare=10.66, unitate=mg/dL
    # ex: "FIER SERIC (SIDEREMIE) [197.52 ug/dL]" -> valoare=197.52
    m_inglobat = re.search(r'\[(\d+[.,]\d+)\s*([a-zA-Z/%µμg·²³]+(?:[/\.][a-zA-Z²³]+)?)\s*\]', linie)
    if m_inglobat:
        # Extrage valoarea corecta din paranteze
        try:
            valoare_reala = float(m_inglobat.group(1).replace(',', '.'))
            unitate_reala = m_inglobat.group(2).strip()
            # Curata denumirea (scoate paranteza cu valoarea din ea)
            denumire = re.sub(r'\s*\[[\d.,]+\s*[^\]]*\]', '', linie).strip()
            denumire = re.sub(r'^["\'\*%\s]+', '', denumire).strip()
            if denumire and len(denumire) >= 2 and not re.match(r'^\d+[.,]?\d*\s*$', denumire):
                return RezultatParsat(
                    denumire_raw=denumire,
                    valoare=valoare_reala,
                    unitate=unitate_reala,
                )
        except ValueError:
            pass

    # Gaseste primul numar izolat (valoarea) - nu face parte din nume
    # Linii de clasificare: "HDL COLESTEROL 68.2 mg/dL > 60 Normal" sau "TRIGLICERIDE 112 mg/dL <150 mg"
    # Acestea contin ANALIZA + valoare + UM + comparator + clasificare => NU sunt rezultate simple
    _CLASIFICARE_RE = re.compile(
        r'\d+[.,]?\d*\s+[a-zA-Z/%µμg·²³]+.*(?:normal|scazut|crescut|optim|borderline|risc|acceptable|'
        r'deficit|toxic|diabet|patolog|referinta|recomandat)',
        re.IGNORECASE
    )
    if _CLASIFICARE_RE.search(linie):
        return None

    # Gaseste primul numar izolat (valoarea) - nu face parte din nume
    # Numele poate contine cifre, dar valoarea e un numar singur dupa spatiu
    m_val = re.search(
        r"(?<!\S)(\d+[.,]\d+|\d+)\s+"        # valoare numerica
        r"([a-zA-Z%µμg·²³'\/][a-zA-Z0-9%µμg·²³'\/\*\.]*)"  # unitate (incepe cu litera/%)
        r"(?:\s+|$)",
        linie
    )
    if not m_val:
        # Incearca sa gaseasca o valoare TEXT (negativ, pozitiv, absent etc.)
        # Format: "NUME ANALIZA [,] VALOARE_TEXT"
        m_text = re.search(
            r"[\s,\.]+(_VALOARE_TEXT_)$".replace(
                "_VALOARE_TEXT_",
                r"(?:negativ[ae]?|pozitiv[ae]?|absent[ae]?|prezent[ae]?|rar[ae]?|"
                r"normal[ae]?|crescut[ae]?|scazut[ae]?|reactiv[ae]?|nedecelabil[ae]?|"
                r"nedetectabil[ae]?|epitelii\s+\w+|leucocite\s+\w+|hematii\s+\w+|"
                r"cilindri\s+\w+|cristale\s+\w+|bacterii\s+\w+|mucus\s+\w+|"
                r"galben[ae]?|incolor[ae]?|tulbure|limpede|clar[ae]?|"
                r"urme|trace[s]?|\<\s*\d[\d\.,]*\s*\w*|\>\s*\d[\d\.,]*\s*\w*)"
            ),
            linie,
            re.IGNORECASE,
        )
        if not m_text:
            return None
        name = linie[:m_text.start()].strip().strip(",.")
        name = re.sub(r'^["\'\*%\s]+', '', name).strip()
        if not name or len(name) < 2 or re.match(r'^\d+[.,]?\d*\s*$', name):
            return None
        valoare_text = m_text.group(1).strip()
        return RezultatParsat(
            denumire_raw=name,
            valoare=None,
            valoare_text=valoare_text,
            unitate=None,
        )

    name = linie[:m_val.start()].strip()
    if not name or len(name) < 2:
        return None

    # Curata artefacte OCR din nume (ghilimele, asteriscuri la inceput)
    name = re.sub(r'^["\'\*%\s]+', '', name).strip()
    if not name or len(name) < 2:
        return None

    # Daca "numele" este doar un numar (ex: "14.2" care e de fapt limita inf referinta),
    # nu este o denumire valida de analiza
    if re.match(r'^\d+[.,]?\d*\s*$', name):
        return None

    try:
        valoare = float(m_val.group(1).replace(",", "."))
    except ValueError:
        return None

    unitate = m_val.group(2) or None
    # Curata unitati cu artefacte OCR (ex. g/'dL → g/dL)
    if unitate:
        unitate = re.sub(r"['\"]", "", unitate).strip() or None

    # Cauta intervalul in restul liniei
    rest = linie[m_val.end():]
    m_interval = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)", rest)
    interval_min = interval_max = None
    if m_interval:
        try:
            interval_min = float(m_interval.group(1).replace(",", "."))
            interval_max = float(m_interval.group(2).replace(",", "."))
        except ValueError:
            pass

    # Valideaza interval (interval_min trebuie < interval_max)
    if interval_min is not None and interval_max is not None:
        if interval_min >= interval_max:
            interval_min = interval_max = None

    # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 citit ca 99)
    valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max, name)

    # Flag H/L — mai intai explicit din text, apoi calculat din interval
    flag = None
    if re.search(r"\bH\b", rest):
        flag = "H"
    elif re.search(r"\bL\b", rest):
        flag = "L"
    elif valoare is not None and interval_min is not None and interval_max is not None:
        if valoare > interval_max:
            flag = "H"
        elif valoare < interval_min:
            flag = "L"

    return RezultatParsat(
        denumire_raw=name,
        valoare=valoare,
        unitate=unitate,
        interval_min=interval_min,
        interval_max=interval_max,
        flag=flag,
    )


# Parametri cu intervale tipice cunoscute (pentru corectie zecimal fara interval in PDF)
# (pattern_substring_in_denumire, valoare_max_tipica) - daca valoare > max*5, incercam /10
_CORECTIE_FARA_INTERVAL = [
    ("rdw", 20.0),       # RDW-CV tipic 11-15%
    ("mpv", 15.0),       # MPV tipic 7-12 fL
    ("pdw", 20.0),       # PDW tipic 9-14 fL
    ("vem", 120.0),      # MCV tipic 80-100 fL
    ("mch", 40.0),       # MCH tipic 27-33 pg
    ("mchc", 40.0),     # MCHC tipic 32-36 g/dL
]


def _corecteaza_decimal_pierdut(valoare: float, interval_min, interval_max, denumire_raw: str = "") -> float:
    """
    Corecteaza erori OCR de tipul '9.9 -> 99' sau '12.4 -> 124' (punct zecimal pierdut).
    Strategii:
    1. Cu interval: daca valoarea e > 10x intervalul_max si valoarea/10 e in interval => divide by 10
    2. Fara interval: euristici pentru RDW, MPV etc. - daca valoare > max_tipic*5, incercam /10
    """
    # Strategie 1: cu interval
    if interval_max is not None and interval_max > 0:
        if valoare > 10 * interval_max:
            v10 = valoare / 10
            if v10 <= 2 * interval_max:
                return v10
            v100 = valoare / 100
            if v100 <= 2 * interval_max:
                return v100
        return valoare

    # Strategie 2: fara interval - euristici pentru parametri cunoscuti
    den_lower = (denumire_raw or "").lower()
    for sub, max_tipic in _CORECTIE_FARA_INTERVAL:
        if sub in den_lower and valoare > max_tipic * 5:
            v10 = valoare / 10
            if v10 <= max_tipic * 2:
                return v10
    return valoare


def extract_rezultate(text: str) -> list[RezultatParsat]:
    """
    Extrage analizele din text. Suporta:
    - Format Bioclinica (2 linii): parametru pe linia i, valoare+UM+interval pe linia i+1
    - Format MedLife/generic (1 linie): parametru + valoare + UM + interval pe aceeasi linie
    Detecteaza automat sectiunile (Hemoleucograma, Biochimie etc.) si le ataseaza
    fiecarui rezultat impreuna cu ordinea din PDF.
    """
    lines = [l.strip() for l in text.replace("\r", "\n").split("\n")]
    results: list[RezultatParsat] = []
    seen: set = set()

    # Urmareste sectiunea curenta pe linii
    # line_sectiune[i] = categoria activa la linia i
    line_sectiune: list[Optional[str]] = [None] * len(lines)
    sectiune_curenta: Optional[str] = None
    for i, linie in enumerate(lines):
        sec = _detecteaza_sectiune(linie)
        if sec:
            sectiune_curenta = sec
        line_sectiune[i] = sectiune_curenta

    ordine_contor = [0]  # folosim lista pt a putea modifica in nested func

    def _key_denumire(raw: str) -> str:
        """Cheie normalizata pentru deduplicare - evita duplicate la variatii OCR (umar->Numar)."""
        s = (raw or "")[:80].lower().strip()
        s = re.sub(r"\bumar\s+de\b", "numar de", s)
        s = re.sub(r"\s*:\s*$", "", s)
        return s

    def _add(r: Optional[RezultatParsat], categorie: Optional[str] = None) -> None:
        if r is None:
            return
        val_key = round(r.valoare, 3) if r.valoare is not None else (r.valoare_text or "")
        key = (_key_denumire(r.denumire_raw or ""), val_key)
        if key not in seen:
            seen.add(key)
            r.categorie = categorie
            r.ordine = ordine_contor[0]
            ordine_contor[0] += 1
            results.append(r)

    # --- Pasul 1: format doua linii Bioclinica ---
    for i in range(1, len(lines)):
        linie_val = lines[i]
        if not linie_val:
            continue

        # Sub-cazul 1b: linia a doua e o valoare TEXT (negativ, pozitiv etc.)
        m_text_linie = _VALOARE_TEXT_RE.match(linie_val.strip())
        if m_text_linie:
            # Nu trata ca valoare text daca linia e parte dintr-o nota explicativa
            _NOTE_EXCLUSE_VAL = re.compile(
                r"absenta\s+oricarei|clasice\s+sau|pe\s+nemancate|medicatii|naturiste|"
                r"intoleranta\s+la|posibila\s+intol|posibil\s+deficit|incidenta\s+scazuta",
                re.IGNORECASE
            )
            if _NOTE_EXCLUSE_VAL.search(linie_val):
                continue
            # Doar linia IMEDIAT precedenta (i-1) - evita swap-uri Param1/Val1 cu Param2/Val2
            # cand OCR/tabel extrage in ordine gresita (ex: Mucus->Rar in loc de Leucocite->Rar)
            denumire = ""
            cat_linie = line_sectiune[i]
            j = i - 1
            if j >= 0:
                cand = lines[j].strip()
                if cand and not _LINIE_NOTA.match(cand):
                    if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand) and not RE_VALOARE_PARTIAL.match(cand):
                        denumire = cand
                        cat_linie = line_sectiune[j]
            if denumire:
                val_key = (_key_denumire(denumire), linie_val.strip().lower())
                if val_key not in seen:
                    seen.add(val_key)
                    r = RezultatParsat(
                        denumire_raw=denumire,
                        valoare=None,
                        valoare_text=linie_val.strip(),
                        unitate=None,
                        categorie=cat_linie,
                        ordine=ordine_contor[0],
                    )
                    ordine_contor[0] += 1
                    results.append(r)
            continue

        m = RE_VALOARE_LINIE.match(linie_val)
        if not m:
            continue
        try:
            valoare = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        unitate = m.group(2).strip().replace(" ", "") or None
        try:
            interval_min = float(m.group(3).replace(",", "."))
            interval_max = float(m.group(4).replace(",", "."))
            # Valideaza intervalul (min trebuie sa fie < max)
            if interval_min >= interval_max:
                interval_min = interval_max = None
        except ValueError:
            interval_min = interval_max = None
        denumire = ""
        cat_linie = line_sectiune[i]
        for j in range(i - 1, max(i - 4, -1), -1):
            cand = lines[j].strip()
            if not cand or _LINIE_NOTA.match(cand):
                continue
            if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand) and not RE_VALOARE_PARTIAL.match(cand):
                denumire = cand
                cat_linie = line_sectiune[j]
            break
        if not denumire:
            continue
        # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 fL citit ca 99)
        valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max, denumire)
        flag_calc = None
        if interval_min is not None and interval_max is not None:
            if valoare > interval_max:
                flag_calc = "H"
            elif valoare < interval_min:
                flag_calc = "L"
        _add(RezultatParsat(
            denumire_raw=denumire,
            valoare=valoare,
            unitate=unitate,
            interval_min=interval_min,
            interval_max=interval_max,
            flag=flag_calc,
        ), categorie=cat_linie)

    # --- Pasul 2: format un singur rand (MedLife, Synevo etc.) ---
    for idx_linie, linie in enumerate(lines):
        if not _este_linie_parametru(linie):
            continue
        r = _parse_oneline(linie)
        _add(r, categorie=line_sectiune[idx_linie])

    return results


def parse_full_text(text: str) -> Optional[PatientParsed]:
    cnp = extract_cnp(text)
    if not cnp:
        return None
    nume, prenume = extract_nume(text)
    rezultate = extract_rezultate(text)
    return PatientParsed(cnp=cnp, nume=nume or "Necunoscut", prenume=prenume, rezultate=rezultate)
