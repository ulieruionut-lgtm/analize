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
    # Antete sectiuni laborator (inclusiv cu diacritice: Hemoleucogramă, Formula leucocitară)
    r"HEMOLEUCOGRAMA|Hemoleucogramă|Formula\s+leucocitară|BIOCHIMIE|IMUNOLOGIE|HORMONI|SUMAR URINA|COAGULARE|"
    r"LIPIDOGRAMA|ELECTROFOREZA|SEROLOGIE|MARKERI|MINERALE|"
    # Note de clasificare (ex: "Crescut : 160-189", "Acceptabil: < 110")
    r"Acceptabil\s*:|Borderline|Crescut\s*[:\(]|Foarte\s+crescut|"
    r"Usor\s+crescut|Moderat\s+crescut|crescute?\s*[>:]|"
    r"Normal\s*:|Optim\s*:|Risc\s*:|Deficit\s+|Nivel\s+toxic|"
    # Note cu sex+varsta: exclude din parametri ca sa nu ajunga "M, 1 an" sau "NITU MATEI M, 1 an" ca rezultat
    # În extract_nume, liniile "NUME M, 1 an" sunt tratate special (nu se exclud din candidati)
    r"^[MF]\s*,\s*\d+\s*(?:ani?|luni?)\s*$|"
    r".*\s[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r"\d{1,3}-\d{1,3}\s+ani|peste\s+\d+\s+ani|trimest|"
    r"persoanelor|persoane\s+varst|"
    # Note diagnostice
    r"Diagnosticul|Glicemie\s+bazala\s+modif|Se\s+recomanda\s+retest|"
    # Artefacte OCR si certificate
    r"Regulamentul\s+nr|CERTIFICAT|certificat|Seria\s+[A-Z]|Nr\.\s+[A-Z]|"
    # Linii administrative laborator
    r"Cod\s+Cerere|Cod\s+Proba|Formular:|Act:\s+[A-Z]|Cont:\s+RO|"
    r"uz\s+personal|executate\s+de\s+parteneri|ghidului\s+KDIGO|"
    r"Data\s+nasterii|Spectrofotome|CITOMETRIE|"
    r"R[ăa]spuns\s+rapid|R[ăa]spuns\s+lent|R[ăa]spuns\s+bifazic|R[ăa]spuns\s+absent|"
    r"Evaluarea\s+r[ăa]spunsului|CRP.ratio|Interpretare:|"
    r"Conform\s+studiilor|favorabil\s+la\s+terapia|tratament\.\s*$|"
    r"Conform\s+studiu|"
    # Header Bioclinica repetat pe fiecare pagina (CNP/Adresa/Trimis/Recoltat etc.)
    r"ANTECEDENT|DATA\s+NA[SȘŞsşș]TERII|^ADRES[AĂ]$|^TRIMIS\s+DE$|"
    r"^RECOLTAT$|^LUCRAT$|^GENERAT$|^CNP$|^NUME$|^PRENUME$|"
    r"^STR\s+|^Str\.\s+|^B-dul\s+|^Calea\s+|"
    r"^medic\s+[A-ZĂÂÎȘȚa-zăâîșț]|^MEDIC\s+[A-ZĂÂÎȘȚ]|"
    r"^\d{5}\s+Laborator|"
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
    r"crescute?\s+\d|Normal\s*[:<>]\s*\d|Optim\s*[:<>]\s*\d|"
    # Gunoi OCR Benchea: linii de interpretare inglobate in text
    r"E\s+Moderat\s+crescut|Interpretare\s+valori\s+glicemie|"
    r"TRIGLICERIDE\s+\d+\s+mg|Bilirubina\s+Negativ\s*:|"
    r"Eritrocite\s+Absente|Leucocite\s+Foarte\s+rare|"
    r"Culoare\*|Claritate\*|Aspect\*|Mucus\s+Absent|"
    r"^\s*rare\s*$|^\s*rara\s*$|^\s*deschis\s*$|^\s*Alte\s*$|"
    r"k\s*=\s*$|k\s*=\s*\d|eGFR:\s*\d+\s*-|"
    # Gunoi OCR Iancu: linii de interpretare si artefacte
    r"Metoda:\s+Reflectometrie|Metoda:\s+Calcul|Metoda:\s+Spectrofotometrie|"
    r"Tip\s+proba:\s+Urina|Tip\s+proba:\s+Ser|"
    r"era,\s*\|\s*negativ|a\)\s*<\s*45\s*-\s*risc|"
    r"Albumina\s+%.*PA\s+E|_Globuline\s+alfa|_UROBILINOGEN,|"
    r"Paisie:|NITRITI,\s*[\"']?negativ|"
    r"30-300\s+crestere\s+moderata|200-240\s+mg|"
    # Linii care sunt footer de pagina cu data embedded
    r"Aceste\s+rezultate\s+pot\s+fi\s+folosite.*Pagina|"
    r"in\s+\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})|"
    # Adrese (Str., Calea, nr/bl, Jud., BRASOV etc.) - OCR: BRASbV
    r"^BRASOV\s|^BRASbV\s|Str\.\s|Calea\s|B-dul\s|nr/?\s*bl|Jud\.|Jud\s|Loc\.|"
    r"^\d+\s+[A-Za-z]+\s+Str\.|^\d+\s+Str\.|"
    # Data eliberarii, Data nastere, Dat nastere (inclusiv "Data. eliberarii")
    r"Data[.,]?\s*eliberarii|Data\s+eliberarii|eliberarii\s+rezultatului|"
    r"Dat\s+nastere|Data\s+nasterii|Data\s+na[sș]terii|"
    # Bioclinica/ clinic + GENERAT + dată
    r"Bioclinica\s+[A-Za-z]+\s+GENERAT|GENERAT\s+\d{2}\.\d{2}\.\d{4}|"
    # Analiza + dată (ex: "Glucază 15.04.2024", "Creatinină serică 10.02.2025")
    r"^[A-Za-zăâîșț]+\s+\d{1,2}\.\d{1,2}\.\d{4}\s*$|"
    # NOTĂ: NU excludem generic „orice linie care se termină cu DD.MM.YYYY” — multe PDF-uri Bioclinica/Synevo
    # pun data recoltării la sfârșitul liniei cu rezultatul; excludeam tot rândul și pierdeam zeci de analize.
    # Data e tăiată în _strip_trailing_date_recoltare() înainte de parsare.
    # Linii care se termină cu dată+oră (ex: "19.02.2026 17:39") - footer generare
    r"^.*\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}\s*$|"
    # Nume laborator (Bioclinica Zărnești etc.) - antet, nu parametru
    r"^Bioclinica\s+\w+\s*$|^Bioclinica\s+\w+\s+GENERAT|"
    # Note explicative (ex: "care iși suplimentează dieta cu creatină.")
    r"care\s+.*creatin|suplimentează\s+dieta|"
    # Unități solitare sau fragmente (mg/dL, (≠ 8.33))
    r"^mg/dL\s*\(|^[a-zA-Z/%µ²³]+/?[a-zA-Z]*\s*\(\s*[≠<>≤≥]|"
    # Intervale/risc fără denumire analiză (doar numere și "risc")
    r"^<?\d{1,3}\s*[-–]?\s*$|^\d{1,3}\s*[-–]\s*\d{1,3}\s+-\s+risc|"
    r"^<\s*45\s*-\s*risc|^45\s*-\s*65\s*-\s*risc|Borderline\s+crescut\s+\d+|"
    # Vârsta pacient (inclusiv "Iancu Gheorghe \"Vârsta: 83 ani,\"")
    r"^[A-ZĂÂÎȘȚ][a-zăâîșț]+\s+[A-ZĂÂÎȘȚ][a-zăâîșț]+.*[Vv][âa]rst|"
    r"[Vv][âa]rst[aă]?\s*:\s*\d+['\s]*ani|Vanta:|"
    r".*Varsta:\s*\d+.*ani|"
    r"^arere\s*:\s*$|"
    # Linii foarte scurte (OCR: prilie, lil) - sub 4 caractere utile
    r"^[a-zA-Z]{1,3}\s*$|^[a-z]{2}\s*$|"
    # Cod Cerere (inclusiv OCR: C'ed Cerere)
    r"C'?ed\s+Cerere|Cod\s+Cerere|"
    # Rezultate pure (valori, nu analize): Negativ, Normal (Normal), Borderline crescut 150
    # OCR: Negatlv, Negat*v
    r"^Negativ\s*$|^Normal\s*$|^Absent\s*$|^Prezent\s*$|"
    r"^Negat[il]v[,:]?\s*mg/dL|^Negativ[,:]?\s*mg/dL|^Negativ\s+mg/dL\s*,\s*AIR|^Negativ:\s*mg/dL\s*,\s*AIR|"
    r"^Normal\s*\(Normal\)\s*$|^Borderline\s+crescut\s+\d+\s*$|"
    # Gunoi OCR: flow citometrie, fragmente tehnice (flowc:tometne, tehnologie: Iaser)
    r"flowcitometrie|flow\s*citometrie|flowc[:\s]tometne|tehnologie:\s*[lI]aser|"
    # Coduri administrative (Act; BV, Sectia) - OCR: Acti BV'
    r"^Act[;i]\s*[A-Z]{2}|"
    # Footer/disclaimer: doza amoxicillin, vârsta cuprinsă - OCR: L'a—varste cupnnse
    r"doza\s*\(0\.5\s*g\s*amox[a-z]*|varste\s*cup[nr]*se|v[aâ]rst[aă]\s*cuprins|^L'[aâ]?\s*[-—]",
    re.IGNORECASE,
)

_LINIE_NOTA = re.compile(r"^\(|^\s*\(")

# Nume pacienți (2+ cuvinte toate majuscule: NITU MATEI, MANDACHE OANA ALEXANDRA)
# Fără IGNORECASE ca să nu excludem "Creatinina urinară"
_RE_NUME_PACIENT_ALL_CAPS = re.compile(r"^[A-ZĂÂÎȘȚ]+\s+[A-ZĂÂÎȘȚ]+(?:\s+[A-ZĂÂÎȘȚ]+)*\s*$")


# Rezultate pure (valori, nu analize) - ex: "Negativ", "Normal (Normal)"
_RE_REZULTAT_PUR = re.compile(
    r"^(Negativ|Normal|Absent|Prezent)\s*$|"
    r"^Negat[il]v[,:]?\s*mg/dL|^Negativ[,:]?\s*mg/dL|^Negativ:\s*mg/dL\s*,\s*AIR|"
    r"^Normal\s*\(Normal\)\s*$|"
    r"^Borderline\s+crescut\s+\d+\s*$|^Borderllne\s+crescut\s+\d+\s*$|"
    r"flowcitometrie|flowc[:\s]tometne|tehnologie:\s*[lI]aser|"
    r"^BRASbV\s|^Act[;i]\s*[A-Z]{2}|"
    r"^Bioclinica\s+[A-Za-zăâîșț]+\s*$|^Bioclinica\s+[A-Za-zăâîșț]+\s+GENERAT|"
    r"Varsta:\s*\d+.*ani|^arere\s*:\s*$|^PETREAN\s+ANA\s+A\s+Varsta",
    re.IGNORECASE,
)


def este_denumire_gunoi(denumire: str) -> bool:
    """
    Returnează True dacă denumirea ar fi exclusă ca parametru (gunoi: nume, adrese,
    date, unități, intervale, rezultate pure, etc.). Folosit pentru curățarea analize_necunoscuta.
    """
    if not denumire or not isinstance(denumire, str):
        return True
    s = denumire.strip()
    if not s:
        return True
    if _LINII_EXCLUSE.match(s):
        return True
    if _RE_NUME_PACIENT_ALL_CAPS.match(s):
        return True
    if _RE_REZULTAT_PUR.match(s):
        return True
    return False


# ─── Recunoastere sectiuni (categorii) din buletine ──────────────────────────
# Mapare: pattern regex -> denumire categorie normalizata
_SECTIUNI = [
    (re.compile(r"HEMATOLOGIE|HEMOLEUCOGRAMA|FORMULA\s+LEUCOCITAR|HEMOGRAM", re.IGNORECASE),
     "Hemoleucograma"),
    (re.compile(
        r"ANALIZA\s+DE\s+URIN|BIOCHIMIE\s+URIN|EXAMEN\s+COMPLET\s+DE\s+URIN|SUMAR\s+URIN|SUMAR\s+SI\s+SEDIMENT|"
        r"SEDIMENT\s+URINAR|SEDIMENT\s+URIN|EXAMEN\s+MICROSCOPIC|^SEDIMENT\s*$|MICROSCOPIE\s+URIN|BIOCHIMIE\s*URINA|URIN[AĂ]",
        re.IGNORECASE,
    ),
     "Examen urina"),
    # Affidea / Hiperdia: bloc creatinină separat de „BIOCHIMIE”
    (re.compile(r"^CREATININ\s*$|^CREATININA\s*$", re.IGNORECASE), "Biochimie"),
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
    # NU include VSH|CRP aici — liniile „VSH” / „CRP” sunt nume de analize; altfel devin „antet” fals
    # și categoria următoarelor rânduri din hemogramă se strică (Capatan și altele).
    (re.compile(r"INFLAMATIE|REACTANTI\s+DE\s+FAZ(?:A)?", re.IGNORECASE),
     "Inflamatie"),
    # Doar antet scurt, nu „Proteina C reactivă cantitativ …” (fără cantitativ = linie analiză)
    (re.compile(
        r"^PROTEINA\s+C\s+REACTIV[aĂă]?(?:\s+CRP)?\s*$",
        re.IGNORECASE,
    ),
     "Inflamatie"),
    (re.compile(r"RAPORT\s+ALBUMIN|MICROALBUMIN", re.IGNORECASE),
     "Examen urina"),
    # MedLife / alte lab: tabel microbiologie (rezultate descriptive pe mai multe linii)
    (re.compile(
        r"^\s*MICROBIOLOGIE\s*$|^\s*Microbiologie\s*$|"
        r"MICROBIOLOGIE\s+(?:SI\s+)?|Sec(?:ți|ti)unea\s+Microbiologie",
        re.IGNORECASE,
    ),
     "Microbiologie"),
]

def _strip_prefix_numar_linie(raw: str) -> str:
    """Elimina prefixe Nr. din format Regina Maria: 1.1.4, 1:2, 1-3, ai:, $.1.11"""
    s = (raw or "").strip()
    m = re.match(r'^((?:ai\s*:\s*)?\$?[\d\.\,\:\-]+\s*\*?\s*)', s, re.IGNORECASE)
    if m:
        rest = s[m.end():].strip()
        if len(rest) >= 2:
            return rest
    return s


def _curata_denumire_rezultat(raw: Optional[str], valoare_text: Optional[str] = None) -> str:
    """
    Elimină din denumirea analizei artefacte OCR: bullet √/✓, rezultat lipit la sfârșit
    când e identic cu valoarea text (ex: «... Trachomatis Negativ» + rezultat Negativ).
    """
    if not raw:
        return ""
    s = raw.strip()
    s = re.sub(r"^[\s\u221A\u2713\u2714\u2610\u2611\u25AA\u2022\*\-\.]+", "", s).strip()
    if valoare_text:
        vt = valoare_text.strip()
        if vt and len(vt) < 50:
            low = s.lower().rstrip(".,;:")
            vlow = vt.lower().rstrip(".,;:")
            for sep in (" ", "-", "–", ":"):
                suf = sep + vlow
                if low.endswith(suf) and len(low) > len(suf) + 3:
                    s = s[: -len(suf)].strip().rstrip("-–: ")
                    break
    return s.strip()


# Linie care nu e parametru ci doar valoare (OCR pe rând greșit)
_RE_DOAR_VALOARE_CA_PARAMETRU = re.compile(
    r"^(?:negativ|pozitiv|absent|prezent|normal|nedecelabil|nedetectabil|reactiv|rară|rar)[ăaei]?\s*$",
    re.IGNORECASE,
)
# Metadate vârstă / sex din antet buletin, nu analiză
_RE_METADATE_VARSTA_LINIE = re.compile(
    r"(?:\bani?\b.*\bluni\b|\bluni\b.*\bani?\b|\bani?\b\s*,\s*\d+\s*luni|"
    r"\(\s*zile\s*\)|\bvârsta\b|\bvarsta\b)",
    re.IGNORECASE,
)


def _detecteaza_sectiune(linie: str) -> Optional[str]:
    """Returneaza numele sectiunii daca linia este un antet de sectiune, altfel None."""
    linie = linie.strip()
    # Antetele de sectiune sunt de obicei scurte (< 80 chars) si fara valori numerice
    if not linie or len(linie) > 100:
        return None
    # Nu trebuie sa contina valori numerice (nu e un rezultat)
    if re.search(r"\d+[.,]\d+|\s\d+\s", linie):
        return None
    # Linii care sunt clar denumiri de analiză, nu antet de bloc (ex: buletine Capatan / Synevo)
    if re.search(r"cantitativ[aă]?\b|cantitativ\b", linie, re.IGNORECASE):
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

# Format valoare + referinta singulara (≤ X) la inceputul liniei - ex: "2,260mg/dL (<= 0,33)"
RE_VALOARE_REF_SINGULAR = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*(?:[≤≥<>]|<=|>=)\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Format valoare simpla fara interval
RE_VALOARE_PARTIAL = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/m]+?)$",
    re.IGNORECASE,
)

# Format Bioclinica: Parametru Valoare UM (min - max) toate pe aceeasi linie
# ex: "Hematii 4.650.000 /mm³ (3.700.000 - 5.150.000)" sau "Hematii 4.650.000/mm3 (3.700.000 - 5.150.000)"
# pdfplumber: valoare lipita de unitate (4.650.000/mm3), unitate cu cifre (mm3)
RE_BIOCLINICA_ONELINE = re.compile(
    r"\s+([\d.,]+)\s*([a-zA-Z0-9/%µμg·²³\u00b3\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Format cu referinta singulara: Valoare UM (≤ X) - ex: "2,260 mg/dL (≤ 0,33)" sau "2,260mg/dL (<= 0,33)"
RE_BIOCLINICA_REF_SINGULAR = re.compile(
    r"\s+([\d.,]+)\s*([a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*(?:[≤≥<>]|<=|>=)\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)


def _parse_european_number(s: str) -> Optional[float]:
    """
    Parseaza numere in format european: 13,3 (virgula=zecimal), 4.650.000 (punct=mii).
    Returneaza float sau None daca nu poate parsa.
    """
    s = (s or "").strip()
    if not s:
        return None
    try:
        if "," in s:
            # Virgula = zecimal: "13,3", "0,27" -> 13.3, 0.27
            # Punct = mii: "4.650.000,5" (rar) - stergem punctele, virgula->punct
            cleaned = s.replace(".", "").replace(",", ".")
            return float(cleaned)
        # Fara virgula: "4.650.000" sau "3.980" sau "81.9"
        cleaned = s.replace(",", ".")
        # Daca are forma d.ddd sau d.ddd.ddd (grupuri de 3 cifre) = mii
        digits_only = re.sub(r"[^0-9]", "", s)
        if len(digits_only) >= 4 and "." in s:
            # Probabil mii: 4.650.000, 323.000, 3.980
            cleaned = s.replace(".", "")
            return float(cleaned)
        return float(cleaned)
    except ValueError:
        return None


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
    r"\s+(?:Medic\s+trimitaro?r?|Medic|Data\s+inregistrari|Data\s+inregistrare|Data\s+tipar|"
    r"Data|Cabinet|Sex|Varsta|Cod|Adresa|Telefon|"
    r"Punctul|Punct|pacient\s*:|Pra\s+pacient|Beneficiar)\s*[:\s]",
    re.IGNORECASE,
)

# Nume care NU sunt nume de persoane - etichete/header-uri OCR
_NUME_GUNOI = re.compile(
    r"^(Data\s+inregistrari[i]?|Data\s+inregistrare|Data\s+tipar|Varsta|CNP|Nume\s*$|"
    r"Prenume\s*$|Adresa|Cod\s+client|Beneficiar)$",
    re.IGNORECASE,
)

# MedLife PDR / antet: după nume apar specialitate sau proceduri separate prin virgulă (OCR le lipește)
_RE_SEGMENT_PROCEDURA_MEDLIFE = re.compile(
    r"(?i)^(OG|Histeroscopie|Colposcopie|Laparoscopie|FIV|IVF|AMIOC|"
    r"Histerosonografie|Ecografie|Consulta|Consultatie|Consult\s|"
    r"Obstetric|Ginecologic|Obstetrica|Chirurgie|Endoscop|Patologie|"
    r"Spitalul|Clinic|Cabinet)\b",
)


def _taie_suffix_medlife_proceduri(s: str) -> str:
    """
    Elimină din coada numelui fragmente tip «OG,Histeroscopie,Colposcopie,FIV» (MedLife).
    Ex: «CHINDRIS ALINA MADALINA OG,Histeroscopie,...» → «CHINDRIS ALINA MADALINA».
    """
    if not s or not s.strip():
        return s or ""
    s = s.strip()
    # OG urmat de listă cu virgulă (frecvent lipit de ultimul prenume)
    s = re.sub(r"\s+OG\s*,.*$", "", s, flags=re.IGNORECASE).strip()
    # Virgulă + proceduri fără OG în față
    s = re.sub(
        r",\s*(?:Histeroscopie|Colposcopie|Laparoscopie|FIV|IVF|Ecografie)\b.*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) <= 1:
        s = re.sub(r"\s+OG\s*$", "", s, flags=re.IGNORECASE).strip()
        return s
    kept: list[str] = []
    for p in parts:
        if _RE_SEGMENT_PROCEDURA_MEDLIFE.match(p):
            break
        p_clean = re.sub(r"\s+OG\s*$", "", p, flags=re.IGNORECASE).strip()
        if p_clean != p:
            kept.append(p_clean)
            break
        kept.append(p)
    return ", ".join(kept) if kept else s


def _curata_nume(raw: str) -> str:
    """Extrage doar numele din text care poate contine 'Medic trimitator:', 'Varsta:', etc."""
    if not raw or not raw.strip():
        return raw or ""
    s = raw.strip()
    # Elimina apostrof/ghilimele parazite la inceput
    s = re.sub(r"^['\u2018\u2019\u201c\u201d\"]+", "", s).strip()
    # Elimina duplicari "Nume pacient: " / "pacient: " la inceput (format Regina Maria)
    while True:
        s2 = re.sub(r"^(?:Nume\s+pacient|pacient)\s*:\s*", "", s, count=1, flags=re.IGNORECASE).strip()
        if s2 == s:
            break
        s = s2
    # Taie tot ce incepe cu "Varsta:" (si duplicatul) - ex: "IANCU Gheorghe 'Varsta: 83 ani, 1 luna Gheorghe 'Varsta: 83 ani, 1 luna"
    s = re.split(r"\s*['\"]?\s*Varsta\s*:", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # Taie la primul "Medic" (trimitaror)
    s = re.split(r"\s+Medic\s+trimitaro?r?\s*", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # Taie si la alte cuvinte-cheie (Data inregistrari, Varsta etc.)
    parts = _NUME_TAIERE.split(s, maxsplit=1)
    s = parts[0].strip()
    # Elimina fragment "M, 1" / "M. 1" / "F, X ani" si repetitiile
    s = re.sub(r"\s+[MF]\s*[.,]\s*\d+\s*(?:ani?|luni?)(?:\s+\w+\s+[MF]\s*[.,]\s*\d+)*\s*$", "", s, flags=re.IGNORECASE).strip()
    # Repetitie "MATEI M, 1" / "M. 1" (punct sau virgula) la sfarsit
    s = re.sub(r"\s+[MF]\s*[.,]\s*\d+\s*(?:\s+\w+\s+[MF]\s*[.,]\s*\d+)*\s*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s+(MATEI|GHEORGHE|ALEXANDRA)\s+[MF]\s*,\s*\d+\s*$", r" \1", s, flags=re.IGNORECASE).strip()
    # Elimina secvente duplicate (ex: "OANA ALEXANDRA CANA ALEXANDRA" - CANA e OCR pentru OANA)
    words = s.split()
    if len(words) >= 4:
        # Daca ultimele 2 cuvinte seamana cu 2 din mijloc (duplicat), le taiem
        last_two = " ".join(words[-2:]).lower()
        for i in range(len(words) - 3):
            mid_two = " ".join(words[i : i + 2]).lower()
            if mid_two == last_two or _similar_ocr(mid_two, last_two):
                s = " ".join(words[: i + 2])
                break
    # Curata artefacte OCR de la sfarsit (apostrof, ghilimele, etc.)
    s = re.sub(r"['\u2018\u2019\u201c\u201d\"]+\s*$", "", s).strip()
    s = re.sub(r"\s+[a-z]{1,2}\s*$", "", s).strip()
    s = re.sub(r"\s+[FM]\s*[|]\s*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*\|\s*$", "", s).strip()
    # Corecteaza erori OCR frecvente la inceput de cuvant
    s = re.sub(r"\blancu\b", "IANCU", s)
    s = re.sub(r"\bvladasel\b", "VLADASEL", s, flags=re.IGNORECASE)
    # MedLife: specialitate / proceduri lipite de Nume/Prenume
    s = _taie_suffix_medlife_proceduri(s)
    return s


def _similar_ocr(a: str, b: str) -> bool:
    """Verifica daca doua cuvinte pereche seamana (ex: cana ~ oana)."""
    if a == b:
        return True
    if len(a) != len(b):
        return False
    diff = sum(1 for x, y in zip(a, b) if x != y)
    return diff <= 1  # maxim 1 litera diferita (OCR)


def _looks_like_analysis(s: str) -> bool:
    """Detecteaza daca textul arata ca denumire de analiza, nu nume pacient (ex: TGO (ASAT))."""
    if not s or len(s) < 3:
        return False
    t = s.strip()
    # Pattern tip analiza: "X (Y)" sau "TGO (ASAT)", "TGP (ALAT)"
    if re.match(r"^[A-Za-z0-9]{2,15}\s*\([A-Za-z0-9/]+\)\s*$", t):
        return True
    # Denumiri scurte de analize (fara paranteze)
    if t.upper() in ("TGO", "TGP", "ASAT", "ALAT", "CRP", "TSH", "MCV", "MCH", "MCHC", "RDW", "HDL", "LDL"):
        return True
    return False


def _curata_camp_prenume(raw: str) -> str:
    """
    Elimină din prenume artefacte OCR frecvente: linia «Prenume:» lipită de «CNP:» repetat,
    fără litere reale de nume.
    """
    if not raw or not raw.strip():
        return ""
    s = raw.strip()
    # Elimină bucle de etichetă CNP la început (ex: «CNP: CNP: 2910808...»)
    for _ in range(8):
        s2 = re.sub(r"^(CNP\s*:?\s*)+", "", s, flags=re.IGNORECASE).strip()
        if s2 == s:
            break
        s = s2
    # CNP lipit de același câmp
    s = re.sub(r"\b[1-8]\d{12}\b", "", s).strip()
    s = re.sub(r"^\s*:\s*", "", s).strip()
    return _curata_nume(s).strip()


def _prenume_invalid(s: Optional[str]) -> bool:
    """True dacă textul nu poate fi un prenume real (etichete OCR, doar «CNP», etc.)."""
    if not s or not str(s).strip():
        return True
    t = str(s).strip()
    if _NUME_GUNOI.match(t.lower()):
        return True
    # Doar repetări CNP / etichete
    if re.match(r"^(?:CNP\s*:?\s*)+$", t, re.IGNORECASE):
        return True
    # Lipsește orice secvență de 2+ litere tip nume propriu (rămân doar etichete/cifre)
    lit = re.sub(r"[^a-zA-ZăâîșțĂÂÎȘȚ]", "", t)
    if len(lit) < 2:
        return True
    # «CNP» repetat, fără nume suficient de lung
    if t.upper().count("CNP") >= 2 and len(lit) < 12:
        return True
    return False


def _nume_e_doar_etichete_ocr(s: str) -> bool:
    """
    True dacă textul e doar etichete luate greșit din formular (ex. «Prenume: CNP: CNP:»
    ajuns în câmpul Nume după OCR).
    """
    if not s or not s.strip():
        return True
    t = re.sub(r"[\s:]+", " ", s.strip().lower())
    tokens = [x for x in t.split() if x]
    if not tokens:
        return True
    # Token-uri care nu pot fi nume proprii (OCR scurt)
    label_only = {"prenume", "nume", "cnp", "cn", "cp"}
    for tok in tokens:
        core = re.sub(r"[^a-zăâîșț]", "", tok)
        if len(core) >= 2 and core not in label_only:
            return False
    return True


def _nume_este_gunoi(nume: str) -> bool:
    """Returneaza True daca numele e eticeta/header, nu nume real."""
    if not nume or len(nume.strip()) < 2:
        return True
    s = nume.strip().lower()
    if _NUME_GUNOI.match(s):
        return True
    if _nume_e_doar_etichete_ocr(nume):
        return True
    if s.startswith("data ") and "inregistr" in s:
        return True
    if "varsta" in s and "ani" in s and len(s) < 50:
        return True
    if s.count(" ") > 5 and ("varsta" in s or "ani" in s):
        return True
    return False


def extract_nume(text: str) -> tuple[str, Optional[str]]:
    """
    Incearca mai intai formatele explicite 'Nume pacient:', 'Nume:' (MedLife, Synevo etc.).
    Dupa aceea cauta backward de la CNP (format Bioclinica).
    """
    def _valid(n: str, p: Optional[str]) -> tuple[str, Optional[str]]:
        if not n or _nume_este_gunoi(n):
            return "Necunoscut", None
        parts = n.split(None, 1)
        return n, (parts[1] if len(parts) >= 2 else None)

    # --- Varianta 1a: "Nume pacient:" (format cu eticheta completa) ---
    m_np = re.search(r"(?:^|\n)\s*Nume\s+pacient\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_np:
        raw_n = _curata_nume(m_np.group(1))
        if raw_n and len(raw_n) >= 2:
            n, p = _valid(raw_n, None)
            if n != "Necunoscut":
                parts = raw_n.split(None, 1)
                return (parts[0], parts[1]) if len(parts) >= 2 else (raw_n, None)
            # Nume pacient: eronat / OCR → încearcă mai jos (CNP etc.)

    # --- Varianta 1a-MedLife: «Nume/Prenume:» (Policlinica PDR, MedLife) ---
    m_slash = re.search(
        r"(?:^|\n)\s*Nume\s*/\s*Prenume\s*:\s*([^\n]+)", text, re.IGNORECASE
    )
    if m_slash:
        raw_np = _curata_nume(m_slash.group(1))
        if raw_np and len(raw_np) >= 2:
            tok = raw_np.split()
            if len(tok) >= 2:
                nume_fam, pren = tok[0], " ".join(tok[1:])
                n, _ = _valid(f"{nume_fam} {pren}".strip(), pren)
                if n != "Necunoscut":
                    return nume_fam, pren

    # --- Varianta 1b: "Nume:" (format scurt) ---
    m_n = re.search(r"(?:^|\n)\s*Nume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    m_p = re.search(r"(?:^|\n)\s*Prenume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_n:
        raw_n = _curata_nume(m_n.group(1))
        if not raw_n:
            raw_n = m_n.group(1).strip()
        prenume = None
        if m_p:
            raw_p = _curata_camp_prenume(m_p.group(1))
            raw_p = re.sub(r"\s+ol\s*$", "", raw_p or "", flags=re.IGNORECASE).strip()
            prenume = raw_p if raw_p and not _prenume_invalid(raw_p) else None
            if prenume and prenume != raw_n:
                n, _ = _valid(f"{raw_n} {prenume}".strip(), prenume)
                if n != "Necunoscut":
                    return n, prenume
        n, _ = _valid(raw_n, None)
        if n != "Necunoscut":
            return n, prenume
        # OCR: «Nume: Prenume: CNP:…» → nu opri aici, caută lângă CNP

    # --- Varianta 2: backward de la CNP (format Bioclinica) ---
    _LINIE_HEADER_NUME = re.compile(
        r"^(Data\s+inregistrari|Data\s+inregistrare|Varsta|CNP|Nume|Prenume|Adresa)\s*$",
        re.IGNORECASE,
    )
    m_cnp = re.search(r"\bCNP\s*:?\s*[1-8]\d{12}\b", text)
    if m_cnp:
        before = text[:m_cnp.start()].strip()
        lines_before = [l.strip() for l in before.split("\n") if l.strip()]
        _LINIE_NUME_CU_VARSTA = re.compile(
            r"^\w+\s+\w+.*\s+[MF]\s*,\s*\d+\s*(?:ani?|luni?)\s*$",
            re.IGNORECASE,
        )
        for linie in reversed(lines_before):
            if re.match(r"^[\d\(]", linie):
                continue
            if _LINIE_HEADER_NUME.match(linie):
                continue
            if _LINII_EXCLUSE.match(linie) and not _LINIE_NUME_CU_VARSTA.match(linie):
                continue
            clean = re.sub(r"\s+[FM],\s*\d+\s*(luni|ani)\s*$", "", linie, flags=re.IGNORECASE).strip()
            clean = _curata_nume(clean)
            if clean and re.search(r"\b[A-ZȘȚĂÂÎ]{2,}", clean) and not _looks_like_analysis(clean):
                n, _ = _valid(clean, None)
                if n != "Necunoscut":
                    parts = clean.split(None, 1)
                    return clean, parts[1] if len(parts) >= 2 else None

    # --- Varianta 3: fallback generic ---
    for pat in [r"(?:Pacient|Beneficiar)\s*[:\-]\s*([^\n]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = _curata_nume(m.group(1))
            n, _ = _valid(raw, None)
            if n != "Necunoscut":
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
        r"homocistein|complement|anticorp|imunoglobul|DAO|VSH|CRP|ALT|AST|GGT|"
        r"chlamydia|mycoplasma|ureaplasma|trachomatis)\b",
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


# Substring-uri care indica gunoi OCR / footer - oriunde in linie
_GUNOI_SUBSTR = (
    "Răspuns rapid", "Răspuns lent", "Răspuns bifazic", "Răspuns absent",  # interpretare CRP
    "M, 1 an", "F, 28 ani", ", 1 an", ", 28 ani",  # sex + varsta
    "BOBEICA", "BCBEIEZA", "Testele cu marcajul", "Aceste rezultate pot fi folosite",
    "doza (0.5 g amoxicillin", "A1 <30: albuminurie", "Pagina ", " din ",
    " spp -", "Enterobacteriaceae -", "micologic", "antibiograma", "nevoie Candida",
    "in 05.01.2026", "in 06.01.2026", "in 22.12.2025",  # disclaimer cu data
)


def _este_linie_parametru(linie: str) -> bool:
    if not linie or len(linie) > 150:
        return False
    if _RE_DOAR_VALOARE_CA_PARAMETRU.match(linie.strip()):
        return False
    if _RE_METADATE_VARSTA_LINIE.search(linie) and len(linie) < 90:
        return False
    if _LINII_EXCLUSE.match(linie):
        return False
    if _RE_NUME_PACIENT_ALL_CAPS.match(linie.strip()):
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
    # Linii cu text foarte scurt si ambiguu (< 3 litere) — exceptie pH (sumar urina)
    _lit = re.sub(r"[^a-zA-Z]", "", linie)
    if len(_lit) < 3 and not re.match(r"^pH\b", linie.strip(), re.IGNORECASE):
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


def _parse_bioclinica_oneline(linie: str) -> Optional[RezultatParsat]:
    """
    Format Bioclinica: Parametru Valoare UM (min - max) sau Valoare UM (≤ X) pe aceeasi linie.
    ex: "Hematii 4.650.000 /mm³ (3.700.000 - 5.150.000)", "Proteina C reactivă 2,260 mg/dL (≤ 0,33)"
    """
    m = RE_BIOCLINICA_ONELINE.search(linie)
    if m:
        val_raw, unitate_raw = m.group(1), m.group(2)
        interval_min = _parse_european_number(m.group(3))
        interval_max = _parse_european_number(m.group(4))
    else:
        m = RE_BIOCLINICA_REF_SINGULAR.search(linie)
        if not m:
            return None
        val_raw, unitate_raw = m.group(1), m.group(2)
        ref = _parse_european_number(m.group(3))
        interval_min = 0 if ref is not None else None
        interval_max = ref

    param_part = linie[: m.start()].strip()
    if not param_part or len(param_part) < 2:
        return None
    if _LINII_EXCLUSE.match(param_part):
        return None
    if _RE_NUME_PACIENT_ALL_CAPS.match(param_part):
        return None

    valoare = _parse_european_number(val_raw)
    if valoare is None:
        return None
    if interval_min is not None and interval_max is not None and interval_min >= interval_max:
        interval_min = interval_max = None

    unitate = unitate_raw.strip() or None
    if unitate:
        unitate = re.sub(r"['\"]", "", unitate).strip() or None

    valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max, param_part)
    valoare = _corecteaza_valoare_hematologie(valoare, unitate, param_part)
    flag = None
    if interval_min is not None and interval_max is not None:
        if valoare > interval_max:
            flag = "H"
        elif valoare < interval_min:
            flag = "L"
    return RezultatParsat(
        denumire_raw=param_part,
        valoare=valoare,
        unitate=unitate,
        interval_min=interval_min,
        interval_max=interval_max,
        flag=flag,
    )


def _parse_oneline(linie: str) -> Optional[RezultatParsat]:
    """
    Parseaza o linie de forma:  NumeAnaliza  Valoare  UM  [Min-Max [UM]] [flag]
    Exemple:
      Hemoglobina 16.4 g/dL 13.0-17.0 g/dl
      Hematocrit 49.1 % 40-50%
      CRP cantitativ 187 mg/L 0-5 mgii
      RDW-CV 144 % 11.5-145%
    Suporta si format Bioclinica: Param Valoare UM (min - max) pe o linie.
    """
    linie = linie.strip()
    if not linie:
        return None

    # Elimina prefix numeric de linie (ex: "9.3 Alfa2-globuline%" -> "Alfa2-globuline%")
    linie = re.sub(r'^\d+\.\d+\s+\*?\s*', '', linie).strip()
    if not linie:
        return None

    # Încearca format Bioclinica: Param Valoare UM (min - max)
    r_bioclinica = _parse_bioclinica_oneline(linie)
    if r_bioclinica is not None:
        r_bioclinica.denumire_raw = _strip_prefix_numar_linie(r_bioclinica.denumire_raw or "")
        if r_bioclinica.denumire_raw and len(r_bioclinica.denumire_raw) >= 2:
            return r_bioclinica

    # Detecteaza valoarea reala inglobata in paranteze patrate in denumire
    # ex: "CALCIU SERIC [10.66 mg/dL]" -> valoare=10.66, unitate=mg/dL
    # ex: "FIER SERIC (SIDEREMIE) [197.52 ug/dL]" -> valoare=197.52
    m_inglobat = re.search(r'\[(\d+[.,]\d+)\s*([a-zA-Z/%µμg·²³]+(?:[/\.][a-zA-Z²³]+)?)\s*\]', linie)
    if m_inglobat:
        valoare_reala = _parse_european_number(m_inglobat.group(1))
        if valoare_reala is None:
            try:
                valoare_reala = float(m_inglobat.group(1).replace(",", "."))
            except ValueError:
                valoare_reala = None
        if valoare_reala is not None:
            unitate_reala = m_inglobat.group(2).strip()
            denumire = re.sub(r'\s*\[[\d.,]+\s*[^\]]*\]', '', linie).strip()
            denumire = re.sub(r'^["\'\*%\s]+', '', denumire).strip()
            if denumire and len(denumire) >= 2 and not re.match(r'^\d+[.,]?\d*\s*$', denumire):
                return RezultatParsat(
                    denumire_raw=denumire,
                    valoare=valoare_reala,
                    unitate=unitate_reala,
                )

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
    name = _strip_prefix_numar_linie(name)
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

    valoare = _parse_european_number(m_val.group(1))
    if valoare is None:
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
        interval_min = _parse_european_number(m_interval.group(1))
        interval_max = _parse_european_number(m_interval.group(2))
        if interval_min is None or interval_max is None:
            try:
                interval_min = float(m_interval.group(1).replace(",", "."))
                interval_max = float(m_interval.group(2).replace(",", "."))
            except ValueError:
                interval_min = interval_max = None

    # Valideaza interval (interval_min trebuie < interval_max)
    if interval_min is not None and interval_max is not None:
        if interval_min >= interval_max:
            interval_min = interval_max = None

    # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 citit ca 99)
    valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max, name)
    # Corecteaza HGB/HCT cu valori 4.x (cifra pierduta)
    valoare = _corecteaza_valoare_hematologie(valoare, unitate, name)

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


def _corecteaza_valoare_hematologie(valoare: float, unitate: Optional[str], denumire_raw: str) -> float:
    """
    Corecteaza valori evident eronate din OCR (cifra pierduta) pentru HGB si HCT.
    - HCT 4.1% -> 44.1% (punct zecimal deplasat)
    - HGB 4.0 g/dL -> 14.0 g/dL (cifra 1 pierduta)
    """
    if valoare is None:
        return valoare
    den = (denumire_raw or "").lower()
    u = (unitate or "").lower()
    # HCT: valorile tipice 35-55%. Daca avem 4.x% => probabil 44.x
    if "hct" in den or "hematocrit" in den:
        if u in ("%",) and 3.5 <= valoare <= 5.5:
            return valoare * 10
    # HGB: valorile tipice 12-18 g/dL. Daca avem 4.x g/dL => probabil 14.x (1 pierdut)
    if "hgb" in den or "hemoglobin" in den:
        if "g/dl" in u and 4.0 <= valoare <= 4.5:
            return valoare + 10
    return valoare


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


_RE_VAL_UM_SIMPLU = re.compile(
    r"^([\d.,]+)\s+([a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(
    # Permite sufixe dupa ')' ca "/mm³", "%", "/L" etc. (format Bioclinica formula leucocitara)
    r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)[^\d\n]*$"
)
_RE_INTERVAL_SINGULAR = re.compile(
    # Format Bioclinica cu referinta singulara: (≤ X) sau (≥ X) sau (< X) sau (> X)
    r"^\(\s*([≤≥<>])\s*([\d.,]+)\s*\)\s*$"
)

# Format pdfplumber formula leucocitara: "Param NUM1 UM1 NUM2 % (INT1)suffix" + urmatoarea "(INT2)%"
# Unitatea poate fi /mm3, /mm³, etc.
_RE_FORMULA_PDFPLUMBER = re.compile(
    r"^([A-Za-zăâîșțĂÂÎȘȚ]+)\s+([\d.,]+)\s*([\/\w³·0-9]+?)\s+([\d.,]+)\s*%\s+\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)


# Sufixe „Data recoltării … DD.MM.YYYY” sau doar dată la sfârșit (Bioclinica, Synevo, Capatan etc.)
_RE_TRAILING_DATE_LABELED = re.compile(
    r"\s+(?:Data\s+(?:recolt(?:are)?|lucr(?:at)?|tipar|generat)[a-zăâîșț]*|Recoltat|Lucrat)\s*:?\s*"
    r"\d{1,2}\.\d{1,2}\.\d{4}(?:\s+\d{1,2}:\d{2})?\s*$",
    re.IGNORECASE,
)
_RE_TRAILING_DATE_EOL = re.compile(r"\s+\d{1,2}\.\d{2}\.\d{4}(?:\s+\d{1,2}:\d{2})?\s*$")


def _strip_trailing_date_recoltare(linie: str) -> str:
    """
    Elimină de la sfârșitul liniei data recoltării / generării (DD.MM.YYYY [HH:MM]),
    astfel încât parserele (Bioclinica oneline, RE_VALOARE_LINIE) să vadă intervalul corect.
    Ex: „Glucoză 92 mg/dL (74-106) 22.02.2024” → „Glucoză 92 mg/dL (74-106)”.
    """
    if not linie or not linie.strip():
        return linie
    s = linie.strip()
    s = _RE_TRAILING_DATE_LABELED.sub("", s).rstrip()
    # Dată la sfârșit fără etichetă — repetă dacă e cazul; nu tăia dacă paranteză deschisă neînchisă
    while s.count("(") <= s.count(")"):
        m = _RE_TRAILING_DATE_EOL.search(s)
        if not m:
            break
        s = s[: m.start()].rstrip()
    return s


def _combina_linii_bioclinica(lines: list) -> list:
    """
    Pre-proceseaza textul Bioclinica care pune valoarea si intervalul pe linii separate.

    Caz 1 (2 linii): 'VALOARE UM' + '(min - max)' -> 'VALOARE UM (min - max)'
    Caz 2 (4 linii - formula leucocitara):
        'VAL_ABS UM_ABS' + 'VAL_PCT %' + '(min-max)UM_ABS' + '(min-max)%'
        -> 'VAL_ABS UM_ABS (min-max)'     (valoarea absoluta)
        -> '{PARAM_PRECEDENT} %'           (duplica parametrul cu sufix %)
        -> 'VAL_PCT % (min-max)'           (valoarea procentuala)
    """
    result = []
    i = 0
    while i < len(lines):
        # Caz 2a: format pdfplumber formula leucocitara (2 linii)
        # "Neutrofile 2.260/mm³ 56,78 % (1.500 - 8.700)/mm³" + "(22,00 - 63,00)%"
        if i + 1 < len(lines):
            mf = _RE_FORMULA_PDFPLUMBER.match(lines[i])
            mi2 = _RE_INTERVAL_PARANTEZE.match(lines[i + 1])
            if mf and mi2:
                param, n1, u1, n2, mn, mx = mf.group(1), mf.group(2), mf.group(3), mf.group(4), mf.group(5), mf.group(6)
                result.append(f"{param} {n1} {u1} ({mn} - {mx})")
                result.append(f"{param} % {n2} % ({mi2.group(1)} - {mi2.group(2)})")
                i += 2
                continue

        # Caz 2b: bloc cu 4 linii (val_abs, val_pct, interval_abs, interval_pct)
        # Forma: "2.260 /mm³" / "56,78 %" / "(1.500 - 8.700)/mm³" / "(22,00 - 63,00)%"
        if i + 3 < len(lines):
            mv1 = _RE_VAL_UM_SIMPLU.match(lines[i])
            mv2 = _RE_VAL_UM_SIMPLU.match(lines[i + 1])
            mi1 = _RE_INTERVAL_PARANTEZE.match(lines[i + 2])
            mi2 = _RE_INTERVAL_PARANTEZE.match(lines[i + 3])
            if mv1 and mv2 and mi1 and mi2:
                # Verifica ca val2 e procentuala (%) si val1 nu e
                um1 = mv1.group(2).strip()
                um2 = mv2.group(2).strip()
                if um2 == "%" and um1 != "%":
                    # Emite val absoluta combinata
                    result.append(f"{lines[i]} ({mi1.group(1)} - {mi1.group(2)})")
                    # Insereaza parametrul duplicat cu sufix % (look-back in result)
                    param_precedent = ""
                    for prev in reversed(result[:-1]):
                        if prev and not _LINII_EXCLUSE.match(prev) and not _RE_NUME_PACIENT_ALL_CAPS.match(prev.strip()):
                            if not RE_VALOARE_LINIE.match(prev) and not _RE_VAL_UM_SIMPLU.match(prev):
                                if len(re.sub(r'[^a-zA-Z]', '', prev)) >= 3:
                                    param_precedent = prev
                                    break
                    if param_precedent:
                        result.append(f"{param_precedent} %")
                    # Emite val procentuala combinata
                    result.append(f"{lines[i + 1]} ({mi2.group(1)} - {mi2.group(2)})")
                    i += 4
                    continue

        # Caz 1a: pereche simpla 'VALOARE UM' + '(min - max)'
        if i + 1 < len(lines):
            m_val = _RE_VAL_UM_SIMPLU.match(lines[i])
            m_int = _RE_INTERVAL_PARANTEZE.match(lines[i + 1])
            if m_val and m_int:
                result.append(f"{lines[i]} ({m_int.group(1)} - {m_int.group(2)})")
                i += 2
                continue
            # Caz 1b: pereche 'VALOARE UM' + '(≤ X)' / '(≥ X)' - ex: Proteina C reactiva
            m_sing = _RE_INTERVAL_SINGULAR.match(lines[i + 1]) if m_val else None
            if m_val and m_sing:
                result.append(f"{lines[i]} ({m_sing.group(1)} {m_sing.group(2)})")
                i += 2
                continue

        result.append(lines[i])
        i += 1
    return result


def _e_nou_rand_test_micro(s: str) -> bool:
    """
    Început de rând tipic în tabelul MedLife Microbiologie (titlu test),
    după care urmează rezultatul pe una sau mai multe linii.
    """
    s = (s or "").strip()
    if not s or len(s) > 200:
        return False
    patterns = (
        r"(?i)^Ex\.\s+microscopic",
        r"(?i)^Examen\s+microbiologic",
        r"(?i)^Ag\s+Chlamydia",
        r"(?i)^Cultura\s+fungi",
        r"(?i)^Mycoplasma\s*/\s*Ureaplasma",
        r"(?i)\(frotiu\)\s*$",
        r"(?i)\(Imunocromatografie\)\s*$",
        r"(?i)\(Identificare/antibiograma\)\s*$",
        r"(?i)\(Cultura\)\s*$",
    )
    return any(re.search(p, s) for p in patterns)


def extract_rezultate(text: str) -> list[RezultatParsat]:
    """
    Extrage analizele din text. Suporta:
    - Format Bioclinica (2 linii): parametru pe linia i, valoare+UM+interval pe linia i+1
    - Format Bioclinica (3 linii): parametru / valoare UM / (min - max) pe linii separate
    - Format MedLife/generic (1 linie): parametru + valoare + UM + interval pe aceeasi linie
    Detecteaza automat sectiunile (Hemoleucograma, Biochimie etc.) si le ataseaza
    fiecarui rezultat impreuna cu ordinea din PDF.
    """
    lines_raw = [_strip_trailing_date_recoltare(l.strip()) for l in text.replace("\r", "\n").split("\n")]
    # Combina perechile 'VALOARE UM' + '(min - max)' intr-o singura linie
    lines = _combina_linii_bioclinica(lines_raw)
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
        r.denumire_raw = _curata_denumire_rezultat(r.denumire_raw, r.valoare_text)
        if not r.denumire_raw or len(r.denumire_raw.strip()) < 2:
            return
        if _RE_DOAR_VALOARE_CA_PARAMETRU.match(r.denumire_raw.strip()):
            return
        if r.valoare is not None:
            val_key: object = round(r.valoare, 3)
        else:
            val_key = (r.valoare_text or "").strip().lower()
        # Include categoria în cheie: aceeași denumire (Leucocite, Hematii, Glucoză) poate apărea
        # în hemogramă și la sumar urină cu aceeași valoare text (ex. „negativ”) — altfel pierdem rânduri.
        cat_key = (categorie if categorie is not None else "") or ""
        key = (_key_denumire(r.denumire_raw or ""), val_key, cat_key)
        if key not in seen:
            seen.add(key)
            r.categorie = categorie
            r.ordine = ordine_contor[0]
            ordine_contor[0] += 1
            results.append(r)

    # --- Pasul 0: MedLife Microbiologie — rezultat descriptiv pe mai multe linii ---
    idx = 0
    while idx < len(lines):
        linie = lines[idx]
        if not linie.strip():
            idx += 1
            continue
        if line_sectiune[idx] != "Microbiologie":
            idx += 1
            continue
        low_head = linie.strip().lower()
        if low_head in ("test", "rezultat", "interval", "interval de referinta", "interval de referință"):
            idx += 1
            continue
        if not _este_linie_parametru(linie) or not _e_nou_rand_test_micro(linie):
            idx += 1
            continue
        test_name = linie.strip()
        j = idx + 1
        parts: list[str] = []
        while j < len(lines):
            if line_sectiune[j] != "Microbiologie":
                break
            ln = lines[j].strip()
            if not ln:
                j += 1
                continue
            if _LINII_EXCLUSE.match(lines[j]):
                break
            if re.match(r"(?i)^Pagina\s+\d", ln):
                break
            if _e_nou_rand_test_micro(ln):
                break
            parts.append(ln)
            j += 1
        if parts:
            blob = "\n".join(parts).strip()[:8000]
            den = _curata_denumire_rezultat(
                _strip_prefix_numar_linie(test_name),
                None,
            )
            if den and len(den) >= 2:
                _add(
                    RezultatParsat(
                        denumire_raw=den,
                        valoare=None,
                        valoare_text=blob,
                        unitate=None,
                    ),
                    categorie="Microbiologie",
                )
            idx = j
        else:
            idx += 1

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
                denumire = _curata_denumire_rezultat(denumire, linie_val.strip())
                if denumire and len(denumire) >= 2 and not _RE_DOAR_VALOARE_CA_PARAMETRU.match(denumire):
                    cat_k = cat_linie or ""
                    tkey = (_key_denumire(denumire), linie_val.strip().lower(), cat_k)
                    if tkey not in seen:
                        seen.add(tkey)
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
        # Daca nu e format min-max, incearca format singular (≤ X) - ex: "2,260mg/dL (<= 0,33)"
        m_sing = None
        if not m:
            m_sing = RE_VALOARE_REF_SINGULAR.match(linie_val) or RE_BIOCLINICA_REF_SINGULAR.match(linie_val)
        if not m and not m_sing:
            continue
        if m:
            valoare = _parse_european_number(m.group(1))
            if valoare is None:
                try:
                    valoare = float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
            unitate = m.group(2).strip().replace(" ", "") or None
            interval_min = _parse_european_number(m.group(3))
            interval_max = _parse_european_number(m.group(4))
            if interval_min is None or interval_max is None:
                try:
                    interval_min = float(m.group(3).replace(",", "."))
                    interval_max = float(m.group(4).replace(",", "."))
                except ValueError:
                    interval_min = interval_max = None
            if interval_min is not None and interval_max is not None and interval_min >= interval_max:
                interval_min = interval_max = None
        else:
            # Format singular (≤ X): valoare si limita superioara
            valoare = _parse_european_number(m_sing.group(1))
            if valoare is None:
                continue
            unitate = m_sing.group(2).strip().replace(" ", "") or None
            interval_min = None
            interval_max = _parse_european_number(m_sing.group(3))
        denumire = ""
        cat_linie = line_sectiune[i]
        # Fereastra extinsa (30 linii) pentru a traversa headerele de pagina Bioclinica
        # care se intercaleaza intre parametru (pagina N) si valoare (pagina N+1)
        for j in range(i - 1, max(i - 30, -1), -1):
            cand = lines[j].strip()
            if not cand or _LINIE_NOTA.match(cand):
                continue
            # Sarim peste linii de header/footer de pagina (nu suntem "blocati")
            if _LINII_EXCLUSE.match(cand):
                continue
            # NU folosi ca parametru o linie care arata ca "Param Val UM (interval)" pe aceeasi linie
            # (format Bioclinica oneline) - altfel riscam: Trombocite pe linia 1, Leucocite pe 2,
            # valoare 267.000 pe 3 -> asociem gresit Leucocite cu 267.000
            if RE_BIOCLINICA_ONELINE.search(cand) or RE_BIOCLINICA_REF_SINGULAR.search(cand):
                break  # e un alt parametru complet - ne oprim
            if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand) and not RE_VALOARE_PARTIAL.match(cand):
                denumire = cand
                cat_linie = line_sectiune[j]
                break  # parametru valid gasit
            # Linie non-exclusa dar nu e parametru valid (data, text descriptiv, etc.)
            # Continuam cautarea inapoi - poate parametrul e mai departe
        if not denumire:
            continue
        # Validare: evita swap Trombocite <-> Leucocite (Trombocite 150k-400k, Leucocite 4k-12k)
        den_lower = denumire.lower()
        if "trombocite" in den_lower or "plt" in den_lower:
            if valoare < 50000 and (interval_max is None or interval_max < 50000):
                continue  # valoarea e pentru Leucocite, nu Trombocite - nu asocia
        if "leucocite" in den_lower:
            if valoare > 50000 or (interval_max is not None and interval_max > 50000):
                continue  # valoarea e pentru Trombocite, nu Leucocite - nu asocia
        denumire = _strip_prefix_numar_linie(denumire)
        denumire = _curata_denumire_rezultat(denumire, None)
        if not denumire or _RE_DOAR_VALOARE_CA_PARAMETRU.match(denumire):
            continue
        # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 fL citit ca 99)
        valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max, denumire)
        valoare = _corecteaza_valoare_hematologie(valoare, unitate, denumire)
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


def parse_full_text(text: str, cnp_optional: bool = False) -> Optional[PatientParsed]:
    """Parsează text PDF. Dacă cnp_optional=True și CNP nu e găsit, folosește un CNP temporar."""
    cnp = extract_cnp(text)
    if not cnp:
        if cnp_optional:
            import uuid
            cnp = "F" + str(uuid.uuid4().int % 10**12).zfill(12)
        else:
            return None
    nume, prenume = extract_nume(text)
    # Siguranță suplimentară: OCR uneori lasă «CNP:» în câmpul Prenume
    if prenume and _prenume_invalid(_curata_camp_prenume(prenume)):
        prenume = None
    rezultate = extract_rezultate(text)
    return PatientParsed(cnp=cnp, nume=nume or "Necunoscut", prenume=prenume, rezultate=rezultate)
