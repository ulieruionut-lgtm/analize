"""Extragere CNP (cu validare), Nume si rezultate analize din text.
Suporta formatele:
 - Bioclinica: parametru pe o linie, valoare + unitate + (interval) pe linia urmatoare
 - MedLife si formate similare: tot pe o linie - Parametru  Valoare  UM  Min-Max UM
"""
import re
from typing import Optional

from backend.models import PatientParsed, RezultatParsat
from backend.ocr_corrections import corecteaza_ocr_linie_buletin, corecteaza_umar_numar_in_denumire

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
    r"Regulamentul\s+nr|CERTIFICAT|certificat|Seria\s+[A-Z]|"
    # Nr. + cod certificat (doar litere MARI) — nu «Nr. eritrocite» (MedLife; re.I făcea «e» = match)
    r"Nr\.\s+(?-i:[A-Z]{2,})(?:\s+[A-Z]{2,})*\s*$|Nr\.\s+(?-i:[A-Z])\s*$|"
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
    # MedLife PDR: note clasificare risc cardiovascular (linii separate sub intervalul de referinta)
    # ex: "Nivel de risc crescut: >=240 mg/dl", "Nivel optim: < 100", "Nivel convenabil: 100-129"
    r"Nivel\s+de\s+risc|Nivel\s+optim\s*:|Nivel\s+convenabil\s*:|Nivel\s+de\s+atentie|"
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
    r"MICROBIOLOGIE|^UROCULTURA\s*$|"
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
    # NU excludem «TRIGLICERIDE 123 mg/dL» — pattern-ul «TRIGL\.\.\.+mg» potrivea și rezultate valide.
    r"E\s+Moderat\s+crescut|Interpretare\s+valori\s+glicemie|"
    r"Bilirubina\s+Negativ\s*:|"
    r"Culoare\*|Claritate\*|Aspect\*|"
    r"^\s*rare\s*$|^\s*rara\s*$|^\s*deschis\s*$|"
    r"k\s*=\s*$|k\s*=\s*\d|eGFR:\s*\d+\s*-|"
    # Gunoi OCR Iancu: linii de interpretare si artefacte
    r"Metoda\s*:|"
    r"Tip\s+proba:\s+Urina|Tip\s+proba:\s+Ser|"
    r"^Proba\s*:\s*[A-Za-zĂÂÎȘȚăâîșț]|"
    r"^Receptionat\s+de\s*:|^Lucrat\s+de\s*:|"
    r"^Examen\s+complet\s+de\s+urin|^Sumar\s*\(urin|^Sediment\s+urinar\s*$|"
    r"era,\s*\|\s*negativ|a\)\s*<\s*45\s*-\s*risc|"
    r"Albumina\s+%.*PA\s+E|"
    r"Paisie:|NITRITI,\s*[\"']negativ|"
    r"30-300\s+crestere\s+moderata|200-240\s+mg|"
    # SCJUB: linii administrative specifice (spital, aparat, doctorand)
    r"^\+\d+\s*,\s*[A-Za-z]|"  # OCR artifact: "+2, Rezultatele se refera strict..."
    r"Cont\s*:\s*RO\d{2}|RO\d{2}\s+TREZ[A-Z0-9]|"  # IBAN cont bancar
    r"COBAS\s*PRO|COBASPRO|"  # Aparat laborator Roche (nu analiza)
    r"CONSILIUL\s+JUDE[TȚŢ]EAN|"  # Institutie administrativa
    r"Tinta\s+terapeutic[aă]\s|"  # Nota clinica target terapeutic
    r"^\d+\s+Dr\.\s+[A-ZĂÂÎȘȚ]|"  # SCJUB: "7 Dr. PIRAU RALUCA" — numar pagina + medic validant
    # Linii care sunt footer de pagina cu data embedded
    r"Aceste\s+rezultate\s+pot\s+fi\s+folosite.*Pagina|"
    r"in\s+\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})|"
    # Adrese (Str., Calea, nr/bl, Jud., BRASOV etc.) - OCR: BRASbV
    r"^BRASOV\s|^BRASbV\s|Str\.\s|Calea\s|B-dul\s|nr/?\s*bl|Jud\.|Jud\s|Loc\.|"
    r"^\d+\s+[A-Za-z]+\s+Str\.|^\d+\s+Str\.|"
    # Data eliberarii, Data nastere, Dat nastere (inclusiv "Data. eliberarii")
    r"Data[.,]?\s*eliberarii|Data\s+eliberarii|eliberarii\s+rezultatului|"
    r"Dat\s+nastere|Data\s+nasterii|Data\s+na[sș]terii|"
    # Bioclinica/ clinic + GENERAT + dată (inclusiv concatenat fara spatii: laboratorBrasovGENERAT)
    r"Bioclinica\s+[A-Za-z]+\s+GENERAT|GENERAT\s+\d{2}\.\d{2}\.\d{4}|"
    r"laborator[A-Za-zĂÂÎȘȚăâîșț]+GENERAT|[A-Za-zĂÂÎȘȚăâîșț]{5,}GENERAT\s*$|"
    # Analiza + dată (ex: "Glucază 15.04.2024", "Creatinină serică 10.02.2025")
    r"^[A-Za-zăâîșț]+\s+\d{1,2}\.\d{1,2}\.\d{4}\s*$|"
    # NOTĂ: NU excludem generic „orice linie care se termină cu DD.MM.YYYY" — multe PDF-uri Bioclinica/Synevo
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
    # Fracție pagina (ex: "1 / 2", "2 / 3") - footer Bioclinica, nu valoare analiză
    r"^\d+\s*/\s*\d+\s*$|"
    # Intervale/risc fără denumire analiză (doar numere și "risc")
    r"^<?\d{1,3}\s*[-–]?\s*$|^\d{1,3}\s*[-–]\s*\d{1,3}\s+-\s+risc|"
    r"^<\s*45\s*-\s*risc|^45\s*-\s*65\s*-\s*risc|Borderline\s+crescut\s+\d+|"
    # Vârsta pacient (inclusiv "Iancu Gheorghe \"Vârsta: 83 ani,\"")
    r"^[A-ZĂÂÎȘȚ][a-zăâîșț]+\s+[A-ZĂÂÎȘȚ][a-zăâîșț]+.*[Vv][âa]rst|"
    r"[Vv][âa]rst[aă]?\s*:\s*\d+['\s]*ani|Vanta:|"
    r".*Varsta:\s*\d+.*ani|"
    r"^arere\s*:\s*$|"
    # MedLife PDR: antet sectiune cu checkmark √ citit de OCR ca litera "V" sau "v"
    # ex: "V Vitamina B12", "V Folat seric", "VVitamingB12" (OCR artefact √+V)
    r"^[vV]\s+[A-Za-zĂÂÎȘȚăâîșț]{4,}|^[vV]{2}[a-zA-ZĂÂÎȘȚăâîșț]{3,}|"
    # Linii foarte scurte (OCR: prilie, lil) — max 2 litere; 3 litere (VEM, MCH, MCV) pot fi analize MedLife
    # Exceptie: «pH» (sumar urină) — altfel se confundă cu gunoi „două litere”
    r"^(?![pP][hH]\s*$)(?![lL][hH]\s*$)[a-zA-Z]{1,2}\s*$|"
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
    r"doza\s*\(0\.5\s*g\s*amox[a-z]*|varste\s*cup[nr]*se|v[aâ]rst[aă]\s*cuprins|^L'[aâ]?\s*[-—]|"
    # Notă clinică / administrativ (nu parametru de laborator — ghid utilizator)
    r"^Observa[tț][ii]\s*$|Observa[tț][ii]\s*:|"
    r"Rezultatul\s+se\s+interpret|interpretare\s+in\s+context\s+clinic|"
    # Cod paraf / Data tipăririi / antete tabel — sursă unică: administrative_fragments
    r"^\s*=\s*$|^\s*ani\s*,\s*3\s*luni\s*$|^\s*\d+\s*ani\s*,\s*\d+\s*luni\s*$|"
    # Zgomot OCR / fragmente ghid (KDIGO), antete false, ore + „Alte cristale"
    r"DNI\s+KDIGO|\bKDIGO\s+guid|\bKDIGO\s*$|"
    r"Diagn[O0]Stipz|Diagnostipz|"
    r"^Diagnostic\s*:\s*$|"
    r"Ă\s+REN\s+Metoda|ĂREN\s+Metoda|"
    r"mfarctulur\s+mrocard|mrocardrc|infarctulur\s+mrocard|"
    r"^\d{3,5}\s+[Cc]elule\s*:|^\d{3,5}\s+[Cc]elule\s|"
    r"^\d{1,2}:\d{2}\s+[Aa]lte\s+crist|"
    # Antete de tabel (PDF text) care nu sunt analize
    r"^Denumire\s+Rezultat(?:\s+UM)?(?:\s+Interval)?|"
    r"^Interval\s+de\s+referin[tț]a|"
    r"^Investigatie\s+Valoare\s+obtinuta|^Investigatie\s+UM\s+Interval|"
    r"^Suma\s+analizelor\s+de\s+pe\s+buletin|"
    r"^\s*✅?\s*TOTAL\s+ANALIZE|"
    r"^Toate\s+valorile\s+sunt\s+extrase|"
    r"^Copii\s+[șs]i\s+adolescen[tț]i|"
    r"^Ser\s*/\s*Metoda|^Ser\s*/\s*metoda|^Ser\s*/\s*Test\s+calculat",
    re.IGNORECASE,
)


_RE_PAGINA_COMPLETA_OCR = re.compile(
    r"Buletin\s+de\s+analize|Punct\s+de\s+recoltare|SANTE\s+VIE|SmartLabs\s+5|"
    r"BULETINDEANALIZE|BuletinDeAnalize|"  # SCJUB: antet PDF concatenat fara spatii
    r"SRENISO|SR\.EN\.ISO",               # SCJUB: SR EN ISO certificare concatenata
    re.IGNORECASE,
)


def _linie_este_exclusa(s: str) -> bool:
    """
    Linie antet administrativ / gunoi: pattern compus _LINII_EXCLUSE
    + fragmente administrative centralizate (fără duplicare regex).
    """
    if not s or not isinstance(s, str):
        return False
    t = s.strip()
    if not t:
        return False
    # Linie masiva OCR (toata pagina pe o linie) — contine antet de laborator
    if len(t) > 400 and _RE_PAGINA_COMPLETA_OCR.search(t):
        return True
    # SCJUB: linii cu text concatenat fara spatii (semn de super-linie OCR), indiferent de lungime
    if re.search(r"BULETINDEANALIZE|SRENISO", t, re.IGNORECASE):
        return True
    # SCJUB: IBAN cont bancar oriunde in linie (prefixe OCR: "wo Cont:", "ai '", etc.)
    if re.search(r"RO\d{2}\s*TREZ\w+\s+Trezoria", t, re.IGNORECASE):
        return True
    # Adresă sediu / punct recoltare (Bioclinica etc.): «_ BRASOV, Str. CALEA BUCUREȘTI, nr/…»
    # Nu e analiză — OCR lipește rândul de adresă sub tabel; _LINII_EXCLUSE e .match(^…) și nu prinde prefixul «_ ».
    if re.search(r"(?i),\s*Str\.?\s+[A-ZĂÂÎȘȚA-Za-zăâîșț]", t):
        return True
    if re.search(r"(?i)\b(Calea|B-dul\.?|Bd\.|Sos\.|Aleea)\s+[A-Za-zĂÂÎȘȚăâîșț]{3,}.+\bnr\.?\s*/", t):
        return True
    m_exc = _LINII_EXCLUSE.match(t)
    # Evită alternativa goală din regex: match de lungime 0 nu înseamnă linie exclusă
    if m_exc is not None and m_exc.end() > 0:
        return True
    if _RE_NUME_MEDIC.match(t):
        return True
    from backend.administrative_fragments import contin_fragment_administrativ

    return contin_fragment_administrativ(t)


_LINIE_NOTA = re.compile(r"^\(|^\s*\(")

# Nume pacienți (2+ cuvinte toate majuscule: NITU MATEI, MANDACHE OANA ALEXANDRA)
# Fără IGNORECASE ca să nu excludem "Creatinina urinară"
_RE_NUME_PACIENT_ALL_CAPS = re.compile(r"^[A-ZĂÂÎȘȚ]+\s+[A-ZĂÂÎȘȚ]+(?:\s+[A-ZĂÂÎȘȚ]+)*\s*$")
_RE_NUME_MEDIC = re.compile(
    r"(?i)^(?:dr\.?|doctor|medic(?:ul)?|medic(?:a)?\s+primar)\s+"
    r"[A-ZĂÂÎȘȚ][A-Za-zĂÂÎȘȚăâîșț'\-]+"
    r"(?:\s+[A-ZĂÂÎȘȚ][A-Za-zĂÂÎȘȚăâîșț'\-]+){1,3}\s*$"
)


# Rezultate pure (valori, nu analize) - ex: "Negativ", "Normal (Normal)"
_RE_REZULTAT_PUR = re.compile(
    r"^(Negativ|Normal|Absent|Prezent)\s*$|"
    r"^Nu\s+s-a\s+detectat\s*$|^Nu\s+s[-a]\s+detectat\s*$|"
    r"^Nu\s+s[-a]\s+decelat\s*$|"
    r"^Culturi\s+bacteriene\s+absente\s*$|^Culturi\s+bacteriene\s+absent[ea]?\s*$|"
    r"^Culturi\s+bacteriene\s+absente\.?\s*$|"
    r"^Relativ\s+frecvente\s*$|^Relativ\s+frecvent[aă]\s*$|"
    r"^Negat[il]v[,:]?\s*mg/dL|^Negativ[,:]?\s*mg/dL|^Negativ:\s*mg/dL\s*,\s*AIR|"
    r"^Normal\s*\(Normal\)\s*$|"
    r"^Borderline\s+crescut\s+\d+\s*$|^Borderllne\s+crescut\s+\d+\s*$|"
    r"flowcitometrie|flowc[:\s]tometne|tehnologie:\s*[lI]aser|"
    r"^BRASbV\s|^Act[;i]\s*[A-Z]{2}|"
    r"^Bioclinica\s+[A-Za-zăâîșț]+\s*$|^Bioclinica\s+[A-Za-zăâîșț]+\s+GENERAT|"
    r"Varsta:\s*\d+.*ani|^arere\s*:\s*$|^PETREAN\s+ANA\s+A\s+Varsta|"
    r"^\d{1,4}\s*$|^\d\s*$",
    re.IGNORECASE,
)


def _este_linie_doar_simboluri(s: str) -> bool:
    """Linie care e doar separator tabel / bifă OCR (nu denumire analiză)."""
    t = (s or "").strip()
    if not t:
        return True
    if t in ("=", "–", "-", "—", ":", ".", "..", "..."):
        return True
    if len(t) <= 8 and re.fullmatch(r"[\s√✓\u221A\u2713\u2714=\-|_\.:·]+", t):
        return True
    return False


def _pare_denumire_analiza_lunga(s: str) -> bool:
    """
    Linii lungi tip laborator (microbiologie, metodă pe aceeași linie) — NU sunt gunoi
    doar pentru că depășesc 14 cuvinte sau 160 caractere.
    """
    low = (s or "").lower()
    return any(
        k in low
        for k in (
            "cultura",
            "microbiologic",
            "chlamydia",
            "mycoplasma",
            "ureaplasma",
            "candida",
            "spectrofotometrie",
            "chemiluminiscenta",
            "chemiluminescenta",
            "tiroxin",
            "bilirubin",
            "tgp",
            "tgo",
            "ft4",
            "egfr",
            "microscopic",
            "citobacteriologic",
            "feritin",
            "glucoz",
            "glicem",
            "absente la",
            "nu s-a detectat",
            "nu s-a decelat",
            "trachomatis",
            "fungi",
            "bacteriene",
            "haemophilus",
            "enterobacter",
            "moraxella",
            "clostridium",
            "toxina",
            "mrsa",
            "gdh",
            "difficile",
        )
    )


def _este_denumire_gunoi_heuristic(s: str) -> bool:
    """
    Reguli suplimentare conservatoare (înaltă precizie): evităm false pozitive
    pe denumiri medicale scurte (ex. pH, VSH, FT4).
    """
    if len(s) <= 1:
        return True
    if "@" in s:
        return True
    if re.search(r"https?://|www\.", s, re.IGNORECASE):
        return True
    lab_lunga = _pare_denumire_analiza_lunga(s)
    if len(s) > (400 if lab_lunga else 160):
        return True
    words = s.split()
    max_cuvinte = 40 if lab_lunga else 14
    if len(words) > max_cuvinte:
        return True
    letters = sum(1 for c in s if c.isalpha())
    if letters == 0 and len(s.strip()) > 2:
        return True
    if re.fullmatch(r"[\d\s\.,;:/\-–\(\)%µ²³°+≥≤]+", s):
        return True
    if re.search(r"\b\d{13}\b", s):
        return True
    if not any(c.isalnum() for c in s):
        return True
    low = s.lower()
    if "pagina" in low and "din" in low and len(s) < 80:
        return True
    if "cod de bare" in low or "cod bare" in low:
        return True
    if "semnatura" in low or "semnătura" in low:
        return True
    # Subtitluri MedLife / copy-paste (nu sunt parametri de catalog)
    # Nu marca «Urocultură» ca gunoi — e denumire legitimă pentru rândul «Rezultat cantitativ: Bacteriurie …».
    if re.match(
        r"(?i)^(bacteriologie\s*[–-]\s*(urocultur|exudat)|"
        r"examen\s+bacteriologic\s*,\s*micologic)\s*$",
        s.strip(),
    ):
        return True
    # Adresă laborator / punct recoltare (ex. «_ BRASOV, Str. CALEA…») — același semnal ca la _linie_este_exclusa
    if re.search(r"(?i),\s*Str\.?\s+[A-ZĂÂÎȘȚA-Za-zăâîșț]", s):
        return True
    # Doar simboluri (tabel OCR degradat)
    if len(s) <= 6 and re.match(r"^[\s√✓\u221A\u2713\u2714=\-|_\.:]+$", s):
        return True
    if _este_linie_doar_simboluri(s):
        return True
    # Text explicativ vaginal / footer (nu parametru de tabel)
    if "microbiotei normale vaginale" in low or (
        "microbiota" in low and "vaginal" in low and "normal" in low
    ):
        return True
    # Legendă interval Feritină (Capatan) extrasă ca pseudo-denumire
    if re.search(r"(?i)femei\s*>\s*\d+\s*ani", s):
        return True
    # OCR: antet «Nume Prenume» lipit de «urină evoluează…» → pseudo-rând «Laza Ana Ramona, ura…»
    if re.search(r"(?i),\s*ura\b", s) or re.search(r"(?i)evolueaz[aă]", s):
        return True
    return False


# Parametri tipăriți ALL CAPS (Regina Maria / Unirea / tabele) — nu sunt „Nume Prenume” pacient.
_RE_ANALIZA_CAPS_EXCLUDE_NUME_PACIENT = re.compile(
    r"(?i)\b("
    r"SERIC|URIC|COLESTEROL|TRANSFERAZA|CREATININ|GLUCOZ|GLICEM|POTASIU|SODIU|TRIGLICER|"
    r"TIROXIN|HEMOGLOB|HEMATOCRIT|ERITROCIT|LEUCOCIT|TROMBOCIT|NEUTROFIL|"
    r"LIMFOCIT|MONOCIT|EOZINOFIL|BAZOFIL|PLACHETAR|ALBUMIN|BILIRUBIN|UROBILIN|"
    r"NITRIT|CORPI|CETON|DENSITAT|URINAR|SPONTAN|RAPORT\s+ALBUMIN|AMINOTRANSFERAZA|"
    r"ASPARTAT|ALANINA|ACID\s+URIC"
    r")\b",
)


def este_denumire_gunoi(denumire: str) -> bool:
    """
    Returnează True dacă denumirea ar fi exclusă ca parametru (gunoi: nume, adrese,
    date, unități, intervale, rezultate pure, etc.). Folosit pentru curățarea analiza_necunoscuta
    și pentru a nu loga necunoscute din normalizer.
    """
    if not denumire or not isinstance(denumire, str):
        return True
    s = denumire.strip()
    if not s:
        return True
    
    # WHITELIST: Acceptă analize medicale cunoscute de scurtă notație
    # (ex: K, Na, pH, Hb, VSH, Ca, Fe, Cl, CO2, etc.)
    # Aceasta previne marcarea pe nedrept ca "gunoi" a codurilor standard medicale
    _VALID_SHORT_NAMES = {
        "K", "Na", "pH", "Hb", "VSH", "Ca", "Fe", "Cl", "CO2", "Mg", "P", "Cr", 
        "BUN", "ALT", "AST", "GGT", "ALP", "CK", "LDH", "Alb", "Glu", "FT3", "FT4",
        "TSH", "PTH", "PSA", "HCG", "AFP", "CEA", "CA19", "INR", "PT", "aPTT",
        "PLT", "WBC", "RBC", "MCV", "MCH", "MCHC", "Hct", "CRP", "ESR", "Eos",
    }
    if s in _VALID_SHORT_NAMES:
        return False
    
    if _linie_este_exclusa(s):
        return True
    if _RE_NUME_PACIENT_ALL_CAPS.match(s):
        # „ACID URIC SERIC”, „HDL COLESTEROL” — caps de laborator, nu pacient ALL CAPS
        if not _RE_ANALIZA_CAPS_EXCLUDE_NUME_PACIENT.search(s):
            return True
    if _RE_REZULTAT_PUR.match(s):
        return True
    if _este_denumire_gunoi_heuristic(s):
        return True
    # Note de clasificare OCR (ex. fragment „crescute” + prag diabetic)
    if re.match(r"(?i)^crescute\s+\d", s):
        return True
    if re.match(r"(?i)^crescute\b", s):
        return True
    return False


# ─── Recunoastere sectiuni (categorii) din buletine ──────────────────────────
# Mapare: pattern regex -> denumire categorie normalizata
_SECTIUNI = [
    (re.compile(r"HEMATOLOGIE|HEMOLEUCOGRAMA|FORMULA\s+LEUCOCITAR|HEMOGRAM", re.IGNORECASE),
     "Hemoleucograma"),
    # Rapoarte compuse (mai multe buletine într-un PDF): subsecțiuni explicite
    (re.compile(r"Imunologie\s*[–-]\s*Markeri\s+Anemie", re.IGNORECASE), "Imunologie si Serologie"),
    (re.compile(r"Imunologie\s*[–-]\s*Markeri\s+Endocrini", re.IGNORECASE), "Hormoni"),
    (re.compile(r"Markeri\s+endocrini\s+suplimentari", re.IGNORECASE), "Hormoni tiroidieni"),
    (re.compile(r"Examen\s+citobacteriologic|citobacteriologic\s+secre", re.IGNORECASE), "Microbiologie"),
    # Secțiuni numerotate (rapoarte structurate / copy-paste din laborator)
    (re.compile(r"^\s*\d+\.\s*Bacteriologie", re.IGNORECASE), "Microbiologie"),
    (re.compile(r"^\s*\d+\.\s*Antibiogram", re.IGNORECASE), "Microbiologie"),
    (re.compile(r"^\s*\d+\.\s*Biochimie\s+seric", re.IGNORECASE), "Biochimie"),
    (re.compile(r"^\s*\d+\.\s*Biochimie\b", re.IGNORECASE), "Biochimie"),
    (re.compile(r"^\s*\d+\.\s*Electroforez", re.IGNORECASE), "Electroforeza"),
    (re.compile(r"^\s*\d+\.\s*Examen\s+complet\s+de\s+urin", re.IGNORECASE), "Examen urina"),
    (re.compile(r"^\s*\d+\.\s*EXAMEN\s+URINAR\s*[-–]\s*SEDIMENT", re.IGNORECASE), "Examen urina sediment"),
    (re.compile(r"^\s*\d+\.\s*Hemoleucogram", re.IGNORECASE), "Hemoleucograma"),
    (re.compile(r"^\s*\d+\.\s*Markeri\s+tumoral", re.IGNORECASE), "Markeri tumorali"),
    (re.compile(r"^\s*\d+\.\s*VSH\b", re.IGNORECASE), "Inflamatie"),
    (re.compile(r"^VSH\s*\(", re.IGNORECASE), "Inflamatie"),
    # După expand tab → spațiu, rândurile «6. Hemoleucogramă» devin «Hemoleucogramă (CBC)» — tot antet de secțiune.
    (re.compile(r"^Hemoleucogram[ăa]?(?:\s*\(|$|\s)", re.IGNORECASE), "Hemoleucograma"),
    (re.compile(r"^Markeri\s+tumoral", re.IGNORECASE), "Markeri tumorali"),
    (re.compile(r"^Antibiogram", re.IGNORECASE), "Microbiologie"),
    # Înainte de pattern-ul generic URIN[AĂ] — altfel «Proba: Urină» din titlul bacteriologiei devine „Examen urină”.
    (re.compile(r"^\s*BACTERIOLOGIE\b|^\s*Bacteriologie\b", re.IGNORECASE), "Microbiologie"),
    # Sub-secțiuni sumar urină (dedupe «Eritrocite» biochimie vs sediment — categorii distincte)
    (re.compile(
        r"SEDIMENT\s+URINAR|SEDIMENT\s+URIN\b|^\s*SEDIMENT\s+URINAR\s*$|^\s*SEDIMENT\s+URIN\s*$|^\s*SEDIMENT\s*$",
        re.IGNORECASE,
    ),
     "Examen urina sediment"),
    (re.compile(r"BIOCHIMIE\s+URIN|BIOCHIMIE\s*URINA", re.IGNORECASE),
     "Examen urina biochimie"),
    (re.compile(
        r"ANALIZA\s+DE\s+URIN|EXAMEN\s+COMPLET\s+DE\s+URIN|SUMAR\s+URIN|SUMAR\s+SI\s+SEDIMENT|"
        r"SUMAR\s*\(\s*URIN|EXAMEN\s+MICROSCOPIC|EXAMEN\s+URINAR|"
        r"MICROSCOPIE\s+URIN|MICROSCOPIE\s+IN\s+FLUX|URIN[AĂ]",
        re.IGNORECASE,
    ),
     "Examen urina"),
    # Affidea / Hiperdia: bloc creatinină separat de „BIOCHIMIE"
    (re.compile(r"^CREATININ\s*$|^CREATININA\s*$", re.IGNORECASE), "Biochimie"),
    (re.compile(r"BIOCHIMIE|BIOCHIMIA|BIOCHIM", re.IGNORECASE),
     "Biochimie"),
    (re.compile(r"LIPIDOGRAM|PROFIL\s+LIPIDIC|LIPIDE", re.IGNORECASE),
     "Lipidograma"),
    (re.compile(r"ELECTROFOREZ", re.IGNORECASE),
     "Electroforeza"),
    (re.compile(r"IMUNOLOGIE\s+SI\s+SEROLOGIE|IMUNOLOGIE|SEROLOGIE", re.IGNORECASE),
     "Imunologie si Serologie"),
    (re.compile(r"HORMONI\s+TIROID|^TIROID", re.IGNORECASE),
     "Hormoni tiroidieni"),
    (re.compile(r"HORMONI|ENDOCRIN|ENDOCRINOLOGIE", re.IGNORECASE),
     "Hormoni"),
    (re.compile(r"COAGULARE|HEMOSTAZ", re.IGNORECASE),
     "Coagulare"),
    (re.compile(r"MARKERI\s+TUMOR|ONCOLOGIC", re.IGNORECASE),
     "Markeri tumorali"),
    (re.compile(r"MINERALE|ELECTROLITI|OLIGOELEMENTE", re.IGNORECASE),
     "Minerale si electroliti"),
    # NU include VSH|CRP aici — liniile „VSH" / „CRP" sunt nume de analize; altfel devin „antet" fals
    # și categoria următoarelor rânduri din hemogramă se strică (Capatan și altele).
    (re.compile(r"INFLAMATIE|REACTANTI\s+DE\s+FAZ(?:A)?", re.IGNORECASE),
     "Inflamatie"),
    # Doar antet scurt, nu „Proteina C reactivă cantitativ …" (fără cantitativ = linie analiză)
    (re.compile(
        r"^PROTEINA\s+C\s+REACTIV[aĂă]?(?:\s+CRP)?\s*$",
        re.IGNORECASE,
    ),
     "Inflamatie"),
    (re.compile(r"RAPORT\s+ALBUMIN|MICROALBUMIN", re.IGNORECASE),
     "Examen urina"),
    # MedLife / alte lab: microbiologie, infecțioase, culturi (titlu secțiune)
    (re.compile(
        r"^\s*MICROBIOLOGIE\s*$|^\s*Microbiologie\s*$|"
        r"MICROBIOLOGIE\s+(?:SI\s+)?|Sec(?:ți|ti)unea\s+Microbiologie|"
        r"INFECȚIOASE|INFECTIOASE|BACTERIOLOG|PARAZITOLOG|VIROLOGIE|"
        r"UROCULT|CULTUR[ĂA]\s+BACTER|ANTIBIOGRAM|EXAMEN\s+CITO\s*BACTER",
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
            s = rest
    # Capatan / tabele: «#PDW», «#Vitamina B12» după prefix numeric
    s = re.sub(r"^#+\s*", "", s).strip()
    return s


def _strip_leading_hash_marker_linie(raw: str) -> str:
    """Elimină markerul «#» din prima coloană tabel (Capatan: #PDW, #PCT, #P-LCR)."""
    s = (raw or "").strip()
    return re.sub(r"^\s*#+(?=[\w\-])", "", s).strip()


def _rewrite_observatii_mucus_capatan(raw: str) -> str:
    """«Observatii Mucus prezent» → rând parsabil ca Mucus (Capatan sediment)."""
    t = (raw or "").strip()
    if not re.match(r"(?i)^observatii\s+", t) or not re.search(r"(?i)\bmucus\b", t):
        return raw
    tail = re.sub(r"(?i)^observatii\s+", "", t).strip()
    tail = re.sub(r"(?i)^mucus\s*", "", tail).strip() or "Prezent"
    return f"Mucus {tail}".strip()


def _lipire_valoare_rand_inainte_de_celule_epiteliale_capatan(lines: list[str]) -> list[str]:
    """
    Capatan: valoarea «Relativ frecvente … Rare» apare pe rândul de deasupra denumirii
    «Celule epiteliale» (tabel fragmentat).
    """
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = (lines[i] or "").strip()
        if i + 1 < len(lines):
            nxt = (lines[i + 1] or "").strip()
            if re.match(r"(?i)^celule\s+epiteliale\s*$", nxt) and re.search(
                r"(?i)relativ\s+frecvente",
                cur,
            ):
                val = re.sub(r"\s+", " ", cur).strip()
                out.append(f"Celule epiteliale {val}")
                i += 2
                continue
        out.append(lines[i])
        i += 1
    return out


def _curata_denumire_rezultat(raw: Optional[str], valoare_text: Optional[str] = None) -> str:
    """
    Elimină din denumirea analizei artefacte OCR: bullet √/✓, rezultat lipit la sfârșit
    când e identic cu valoarea text (ex: «... Trachomatis Negativ» + rezultat Negativ).
    """
    if not raw:
        return ""
    s = raw.strip()
    s = _RE_STRIP_PREFIX_SIMBOLURI.sub("", s).strip()
    if valoare_text:
        vt = valoare_text.strip()
        if vt and len(vt) < 50:
            low = s.lower().rstrip(".,;:")
            vlow = vt.lower().rstrip(".,;:")
            for sep in (" ", "\t", "-", "–", ":"):
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
    linie_orig = linie.strip()
    if not linie_orig:
        return None
    # Antet + valoare pe același rând (ex. «V. Markeri … : 0,482 ng/ml») — sub ~100 caractere dar cu «: valoare» tot trebuie trunchiat.
    linie_work = linie_orig
    if len(linie_orig) > 80 and re.search(r":\s*[\d<>+±≤≥]", linie_orig):
        parts = re.split(r":\s*(?=[\d<>+±≤≥])", linie_orig, maxsplit=1)
        probe = parts[0].strip() if parts else linie_orig
        if len(probe) >= 12:
            linie_work = probe
    # «3. Biochimie serică» / «6. Hemoleucogramă» — pattern-urile cu ^\s*\d+\. trebuie testate pe linia integrală;
    # după eliminarea «N. » nu se mai potrivesc și categoria rămâne greșită pentru tot blocul.
    for pattern, categorie in _SECTIUNI:
        if pattern.search(linie_orig):
            return categorie
    # Numerotare tip 1. / 1.1 / 1.2.3 pe același rând cu titlul (TEO HEALTH, Regina Maria, etc.).
    # Fără asta, „1.1 Sumar (urina)” conține „1,1” în testul numeric de mai jos și nu mai e recunoscută ca secțiune.
    linie = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", linie_work).strip()
    linie = re.sub(r"^\*+\s*", "", linie).strip()
    if not linie:
        linie = linie_work
    # Nu trebuie sa contina valori numerice (nu e un rezultat) — exceptie: antete microbiologie cu UFC în text.
    if re.search(r"\d+[.,]\d+|\s\d+\s", linie) and not re.search(
        r"(?i)bacteriologie|microbiologie|urocultur|antibiogram",
        (linie[:50] if linie else ""),
    ):
        return None
    # Linii care sunt clar denumiri de analiză, nu antet de bloc (ex: buletine Capatan / Synevo)
    if re.search(r"cantitativ[aă]?\b|cantitativ\b", linie, re.IGNORECASE):
        return None
    for pattern, categorie in _SECTIUNI:
        if pattern.search(linie):
            return categorie
    return None

# Valori text frecvente in analizele medicale (sumar urina, culturi, etc.)
# Ancoră obligatorie la sfârșit ($): fără ea, `uro\s*\d*` potrivea prefixul „Uro” din „Urocultura”
# și Pasul 1b asocia greșit valori text cu rândul anterior.
_VALOARE_TEXT_RE = re.compile(
    r"^(negativ[ae]?|pozitiv[ae]?|absent[ae]?|absen[țt]i|prezent[ae]?|rar(?:[ae]|i)?|frecvente?|normal[ae]?|"
    r"crescut[ae]?|scazut[ae]?|reactiv[ae]?|nedecelabil[ae]?|nedetectabil[ae]?|"
    r"nu\s+se\s+observ[aă]?|"
    r"galben[ae]?|incolor[ae]?|tulbure|limpede|clar[ae]?|"
    r"urme|trace[s]?|"
    r"\+{1,4}[-+]?\d*|"
    r"[<>]\s*\d+[\.,]?\d*\s*\w*)\s*$",
    re.IGNORECASE,
)

# UM tip «×10⁶/µL» / «x10^3/µL» (rapoarte digitale, Markdown)
_RE_UM_X10_SLASH = r"(?:[×x]\s*10(?:\^[\d]+|[\u2070-\u2079\u00b2\u00b3\u00b9]+)/[\wµμ/L·²³]+)"

# Format Bioclinica: valoare+unitate + interval in paranteza
RE_VALOARE_LINIE = re.compile(
    r"^([\d.,]+)\s*"
    r"((?:" + _RE_UM_X10_SLASH + r")|\*[\w/.^µμ·]+|[a-zA-Z0-9/%µμg·²³\u00b3\s/]+?)\s*"
    r"\(\s*([\d.,]+)\s*[-–−]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# MedLife / tabele: valoare + UM + min - max FĂRĂ paranteze (ex: «4.66 *10^6/µL 3.9 - 5.3»)
RE_VALOARE_LINIE_DASH = re.compile(
    r"^\s*(?:[<>≤≥]\s*)?([\d.,]+)\s+"
    r"(.+?)\s+"
    r"([\d.,]+)\s*[-–]\s*([\d.,]+)\b",
    re.IGNORECASE,
)

# În _este_gunoi_ocr: rând «valoare UM min - max» oriunde în linie (fără _parse_oneline — evită cicluri/cost la pornire)
_RE_TABULAR_ROW_VAL_UM_INTERVAL = re.compile(
    r"(?<!\S)(?:[<>≤≥]\s*)?(?:\d+[.,]\d+|\d+)\s+"
    r"(?:" + _RE_UM_X10_SLASH + r"|\*[\w/.^µμ·]+|[a-zA-Z%µμg·²³'\/][\w/.^µμ³·/%]*)\s+"
    r"[\d.,]+\s*[-–]\s*[\d.,]",
    re.IGNORECASE,
)

# Format valoare + referinta singulara (≤ X) la inceputul liniei - ex: "2,260mg/dL (<= 0,33)"
# Permite sufix "+N" sau "-N" inainte de ")" (Bioclinica: "22,60 mg/L (≤ 3,30 +1)")
RE_VALOARE_REF_SINGULAR = re.compile(
    r"^([\d.,]+)\s*((?:" + _RE_UM_X10_SLASH + r")|\*[\d^/µμ\w\.·]+|[a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*(?:[≤≥<>]|<=|>=)\s*([\d.,]+)\s*(?:[+\-]\d+)?\s*\)",
    re.IGNORECASE,
)

# Format valoare simpla fara interval (inclusiv UM tip *10^3/µL sau ×10³/µL)
RE_VALOARE_PARTIAL = re.compile(
    r"^\s*(?:[<>≤≥]\s*)?([\d.,]+)\s+(" + _RE_UM_X10_SLASH + r"|\*[\w/.^µμ³·]+|[a-zA-Z/%µμg·²³][\w/.^µμ³·\s/m]*)$",
    re.IGNORECASE,
)

# Format Bioclinica pdfplumber: valoare lipita de unitate cu slash, fara spatiu, fara interval pe linie
# ex: "4.650.000/mm3", "323.000/mm3", "3.980/mm3", "2.260/mm3"
RE_VALOARE_SLASH_UNIT = re.compile(
    r"^([\d.,]+)/([a-zA-Z0-9µμ³²]+)\s*$",
    re.IGNORECASE,
)

# Format Bioclinica: Parametru Valoare UM (min - max) toate pe aceeasi linie
# ex: "Hematii 4.650.000 /mm³ (3.700.000 - 5.150.000)" sau "Hematii 4.650.000/mm3 (3.700.000 - 5.150.000)"
# pdfplumber: valoare lipita de unitate (4.650.000/mm3), unitate cu cifre (mm3)
RE_BIOCLINICA_ONELINE = re.compile(
    r"\s+([<>≤≥]?\s*[\d.,]+)\s*((?:" + _RE_UM_X10_SLASH + r")|\*[\d^/µμ\w\.·]+|[a-zA-Z0-9/%µμg·²³\u00b3\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Format cu referinta singulara: Valoare UM (≤ X) - ex: "2,260 mg/dL (≤ 0,33)" sau "2,260mg/dL (<= 0,33)"
RE_BIOCLINICA_REF_SINGULAR = re.compile(
    r"\s+([\d.,]+)\s*((?:" + _RE_UM_X10_SLASH + r")|\*[\d^/µμ\w\.·]+|[a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*(?:[≤≥<>]|<=|>=)\s*([\d.,]+)\s*\)",
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
    # Valori cu < sau > (ex: "< 8", "> 60") — pastram valoarea numerica
    s = re.sub(r"^[<>≤≥]\s*", "", s)
    if not s:
        return None
    # Corecție OCR conservatoare: litere confundate cu cifre.
    # Aplicăm DOAR dacă stringul conține cel puțin o cifră reală,
    # ca să nu modificăm texte/denumiri care nu sunt numere.
    if re.search(r'\d', s):
        s = s.replace('O', '0').replace('o', '0')                  # O → zero
        s = re.sub(r'(?<![a-zA-Z])l(?![a-zA-Z])', '1', s)          # l izolat → 1 (nu în mL, pmol...)
        s = re.sub(r'(?<![a-zA-Z])I(?![a-zA-Z])', '1', s)          # I izolat → 1
    try:
        if "," in s:
            # Virgula = zecimal: "13,3", "0,27" -> 13.3, 0.27
            # Punct = mii: "4.650.000,5" (rar) - stergem punctele, virgula->punct
            cleaned = s.replace(".", "").replace(",", ".")
            return float(cleaned)
        # Fara virgula: "4.650.000" sau "3.980" sau "81.9"
        cleaned = s.replace(",", ".")
        # Punct de mii: toate grupurile dupa punct au exact 3 cifre
        # ex: "3.980" (3 cifre dupa punct) sau "4.650.000" (grupuri de 3)
        # ATENTIE: "14.89" (2 cifre) sau "0.27" (2 cifre) = format standard cu punct zecimal
        parts_after_dot = re.findall(r"\.(\d+)", s)
        if parts_after_dot:
            last_group_len = len(parts_after_dot[-1])
            # Un singur punct + exact 3 cifre după: «1.023» (densitate urină), nu separator de mii
            if last_group_len == 3 and s.count(".") == 1:
                return float(cleaned)
            if last_group_len == 3:
                # Ex.: «4.650.000» — mai multe grupuri de câte 3 cifre
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
    hits = enumerare_cnp_valide_ordine_aparitie(text)
    return hits[0] if hits else None


def enumerare_cnp_valide_ordine_aparitie(text: str) -> list[str]:
    """
    Toate CNP-urile valide **distincte**, în ordinea primei apariții în text
    (pass normal + pass corecție OCR ca la extract_cnp).
    """
    raw = text or ""
    ordered: list[str] = []
    seen: set[str] = set()

    def _push_from_source(src: str) -> None:
        for m in re.finditer(r"\b[1-8]\d{12}\b", src):
            c = m.group()
            if validare_cnp(c) and c not in seen:
                seen.add(c)
                ordered.append(c)

    _push_from_source(raw)
    text_fix = re.sub(
        r"\b[1-8O][0-9OolI1B]{11}[0-9OolI1B]\b",
        lambda m: m.group()
        .replace("O", "0")
        .replace("o", "0")
        .replace("l", "1")
        .replace("I", "1")
        .replace("B", "8"),
        raw,
    )
    _push_from_source(text_fix)
    return ordered


def numara_matchuri_cnp_valide(text: str) -> int:
    """Numără aparițiile CNP valide (poziție + șir), după deduplicare între pass normal și OCR."""
    raw = text or ""
    hits: set[tuple[int, str]] = set()
    for m in re.finditer(r"\b[1-8]\d{12}\b", raw):
        if validare_cnp(m.group()):
            hits.add((m.start(), m.group()))
    text_fix = re.sub(
        r"\b[1-8O][0-9OolI1B]{11}[0-9OolI1B]\b",
        lambda m: m.group()
        .replace("O", "0")
        .replace("o", "0")
        .replace("l", "1")
        .replace("I", "1")
        .replace("B", "8"),
        raw,
    )
    for m in re.finditer(r"\b[1-8]\d{12}\b", text_fix):
        if validare_cnp(m.group()):
            hits.add((m.start(), m.group()))
    return len(hits)


# Cuvinte-cheie dupa care taiem (nu fac parte din numele pacientului)
# «Medicitrimitator» = OCR fără spațiu între Medic și trimitator (foarte frecvent pe buletine)
_NUME_TAIERE = re.compile(
    r"\s+(?:Medicitrimitator|Medic\s+trimitaro?r?|Medic|Data\s+inregistrari|Data\s+inregistrare|Data\s+tipar|"
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
    r"Spitalul|Clinic|Cabinet|materno[\s\-]?fetala|rejuvenare|uroginecolog|perineolog)\b",
)


def _taie_suffix_medlife_proceduri(s: str) -> str:
    """
    Elimină din coada numelui fragmente tip «OG,Histeroscopie,Colposcopie,FIV» (MedLife).
    Ex: «CHINDRIS ALINA MADALINA OG,Histeroscopie,...» → «CHINDRIS ALINA MADALINA».
    """
    if not s or not s.strip():
        return s or ""
    s = s.strip()
    # Sufixe procedurale frecvente (MedLife) lipite de nume
    s = re.sub(
        r"\s+(?:materno[\s\-]?fetala|rejuvenare\s+vaginala|uroginecolog(?:ie)?|perineolog(?:ie)?)\b.*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
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
    
    # ─── CURATENIE AGRESIVA LA INCEPUT ───
    # Elimina garbage OCR la inceput: "rii i ", "pl ", "ll ", "ti ", "it ", etc.
    s = re.sub(r"^[a-z]{1,3}\s+[a-z]?\s*", "", s).strip()
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
    # OCR: «Medicitrimitator» (fără spațiu) — taie înainte de medic trimitător
    s = re.split(r"\s*Medicitrimitator\s*", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # Taie la primul "Medic" (trimitător), cu sau fără spațiu între cuvinte
    s = re.split(r"\s+Medic\s*trimitaro?r?\s*", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # «Dr:» / «Dr-:» urmat de nume medic (nu pacient)
    s = re.split(r"\s+Dr[\s.\-]*:\s*", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # Taie si la alte cuvinte-cheie (Data inregistrari, Varsta etc.)
    parts = _NUME_TAIERE.split(s, maxsplit=1)
    s = parts[0].strip()
    
    # ─── CURATENIE AGRESIVA LA SFARSIT ───
    # Elimina pattern "7.) ST on ete, srs" - numerotare + garbage
    s = re.sub(r"\s+\d+\.\s*\)\s+[A-Z]{1,3}\s+on\s+\w+[,\s].*$", "", s, flags=re.IGNORECASE).strip()
    # Elimina "7.) ST" pattern - numar cu paranteaza + litere
    s = re.sub(r"\s+\d+\.\s*\)\s+\w+\s*$", "", s).strip()
    # Elimina secvente ciudate la sfarsit: "ST on ete, srs"
    s = re.sub(r"\s+(?:ST|on|ete|srs|TT|ll|ii)[\s,]*$", "", s, flags=re.IGNORECASE).strip()
    
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
    
    # OCR: dublare prenume după tăiere sufix (ex: "TUTUNGIU GABRIELA CRISTINA GABRIELA CRISTINA")
    toks = s.split()
    if len(toks) >= 5:
        rest = toks[1:]
        if len(rest) % 2 == 0:
            half = len(rest) // 2
            if rest[:half] == rest[half:]:
                s = " ".join([toks[0]] + rest[:half])
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
    raw = nume.strip()
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
    # OCR: câmp medic trimitător lipit de nume
    if "medicitrimitator" in s.replace(" ", "") or "trimitator" in s:
        return True
    # Paranteze goale + text (ex: RAG()MIR) — aproape niciodată nume real
    if re.search(r"\(\)\s*\w", raw):
        return True
    # Mult zgomot tip OCR: puncte duble, underscore în „cuvinte", pipe
    if ".." in raw and len(raw) > 25:
        return True
    if re.search(r"\b[A-Za-zăâîșț]{2,}_+[A-Za-zăâîșț]", raw):
        return True
    if "|" in raw or "¬" in raw:
        return True
    # Prea multe semne non-literă față de litere (nume corupt)
    lit = re.sub(r"[^a-zA-ZăâîșțĂÂÎȘȚ]", "", raw)
    nonlit = len(re.sub(r"[a-zA-ZăâîșțĂÂÎȘȚ\s]", "", raw))
    if len(lit) >= 4 and nonlit > len(lit):
        return True
    return False


def _sanitize_nume_prenume_final(nume: str, prenume: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Curățare finală defensivă (post-extracție) pentru cazuri OCR unde specialități/proceduri
    rămân lipite de nume sau se dublează fragmentele de prenume.
    """
    full = " ".join([x for x in [(nume or "").strip(), (prenume or "").strip()] if x]).strip()
    if not full:
        return (nume or "").strip(), (prenume or None)
    # taie orice după tokeni procedurali (indiferent de punctuație/case)
    full = re.sub(
        r"(?i)\b(materno[\s\-]?fetala|rejuvenare|uroginecolog(?:ie)?|perineolog(?:ie)?)\b.*$",
        "",
        full,
    ).strip(" ,;:-")
    # dedupe pe jumătate: "X Y Z Y Z"
    toks = full.split()
    if len(toks) >= 5:
        rest = toks[1:]
        if len(rest) % 2 == 0:
            h = len(rest) // 2
            if [x.lower() for x in rest[:h]] == [x.lower() for x in rest[h:]]:
                full = " ".join([toks[0]] + rest[:h]).strip()
    parts = full.split(None, 1)
    if not parts:
        return (nume or "").strip(), (prenume or None)
    return parts[0], (parts[1] if len(parts) > 1 else None)


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

    # --- Varianta 0: Regina Maria OCR — «Nume:\n<valoare>» (eticheta pe linie separata) ---
    # Tesseract cu PSM 6 pe formular cu 2 coloane poate separa eticheta de valoare pe linii distincte.
    # Acceptă TitleCase SAU ALL CAPS (ambele apar din OCR pe scane Regina Maria).
    m_rm = re.search(
        r"(?:^|\n)\s*Nume\s*:\s*\n\s*([A-ZĂÂÎȘȚ][a-zA-ZăâîșțĂÂÎȘȚ]+(?:[\s\-][A-ZĂÂÎȘȚ][a-zA-ZăâîșțĂÂÎȘȚ]+)+)",
        text,
    )
    if not m_rm:
        # ALL CAPS pe linie separată: CRETULESCU CORNEL
        m_rm = re.search(
            r"(?:^|\n)\s*Nume\s*:\s*\n\s*([A-ZĂÂÎȘȚ]{2,}(?:\s+[A-ZĂÂÎȘȚ]{2,})+)",
            text,
        )
    if m_rm:
        raw_rm = _curata_nume(m_rm.group(1))
        n_rm, _ = _valid(raw_rm, None)
        if n_rm != "Necunoscut":
            parts_rm = raw_rm.split(None, 1)
            return raw_rm, parts_rm[1] if len(parts_rm) >= 2 else None

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
    # Regina Maria OCR: PSM 6 pe layout 2 coloane poate pune «Nume: Cretulescu Cornel CNP: ...»
    # toate pe aceeași linie (fără newline). Regex-ul nu mai cere start-de-linie.
    # Capturăm tot până la primul CNP:/Varsta:/Sex: de pe aceeași linie.
    # IMPROVED: Only capture valid name patterns (capitalized words) instead of all garbage
    m_n = re.search(
        r"\bNume\s*:\s*([A-ZĂÂÎȘȚ][A-Za-zăâîșțĂÂÎȘȚ\s\-]*?)(?:\s+\d+\.\s*\)|CNP\s*:|Varsta\s*:|Sex\s*:|Prenume\s*:|$)",
        text,
        re.IGNORECASE,
    )
    m_n_next = re.search(r"(?:^|\n)\s*Nume\s*:\s*\S[^\n]*\n\s*([A-ZĂÂÎȘȚ][a-zăâîșț]+(?:\s+[A-ZĂÂÎșț][a-zăâîșț]+)+)", text, re.IGNORECASE)
    m_p = re.search(r"(?:^|\n)\s*Prenume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_n:
        raw_n = _curata_nume(m_n.group(1))
        if not raw_n:
            raw_n = m_n.group(1).strip()
        # ALL CAPS inline: «Nume: CRETULESCU CORNEL» — _curata_nume poate respinge ALL CAPS,
        # deci dacă raw_n e invalid dar grupul arată ca ALL CAPS, îl preluăm direct.
        if not raw_n or raw_n == m_n.group(1).strip():
            grp = m_n.group(1).strip()
            if re.match(r"^[A-ZĂÂÎȘȚ]{2,}(?:\s+[A-ZĂÂÎȘȚ]{2,})+$", grp):
                raw_n = grp
        # Fallback: daca valoarea de pe aceeasi linie nu e un nume valid, verifica linia urmatoare
        n_test, _ = _valid(raw_n, None)
        if n_test == "Necunoscut" and m_n_next:
            raw_n_next = _curata_nume(m_n_next.group(1))
            n_next, _ = _valid(raw_n_next, None)
            if n_next != "Necunoscut":
                parts_next = raw_n_next.split(None, 1)
                return raw_n_next, parts_next[1] if len(parts_next) >= 2 else None
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

    # --- Varianta 2a: Bioclinica header — «NUME [MF], N ani  Buletin de analize ...» (prima linie) ---
    # Bioclinica pune pe prima linie: MANDACHE OANA ALEXANDRA   F, 28 ani  Buletin de analize 26219B0409 din ...
    # _LINII_EXCLUSE prinde toata linia (contine « F, 28 ani»), deci trebuie detectata explicit.
    m_bio = re.search(
        r"^([A-ZĂÂÎȘȚ][A-ZĂÂÎȘȚ\s\-]{3,}?)\s+[MF]\s*,\s*\d+\s*(?:ani?|luni?)\b",
        text[:800],
        re.MULTILINE,
    )
    if m_bio:
        raw_bio = _curata_nume(m_bio.group(1).strip())
        n_bio, _ = _valid(raw_bio, None)
        if n_bio != "Necunoscut":
            parts_bio = raw_bio.split(None, 1)
            return raw_bio, (parts_bio[1] if len(parts_bio) >= 2 else None)

    # --- Varianta 2: backward de la CNP (format Bioclinica / Regina Maria 2 coloane) ---
    # Regina Maria OCR: «CNP:» și numărul pot fi pe linii separate → căutăm fie
    # «CNP: <număr>» pe aceeași linie, fie direct poziția primului CNP valid în text.
    _LINIE_HEADER_NUME = re.compile(
        r"^(Data\s+inregistrari|Data\s+inregistrare|Varsta|CNP|Nume|Prenume|Adresa)\s*$",
        re.IGNORECASE,
    )
    cnp_val = extract_cnp(text)
    m_cnp = re.search(r"\bCNP\s*:?\s*[1-8]\d{12}\b", text)
    if not m_cnp and cnp_val:
        # CNP-ul e pe o linie separată față de eticheta "CNP:" — găsim poziția numărului
        m_cnp = re.search(re.escape(cnp_val), text)
    if m_cnp:
        before = text[:m_cnp.start()].strip()
        lines_before = [l.strip() for l in before.split("\n") if l.strip()]
        # Fara ancora $ — prinde si liniile cu text suplimentar dupa varsta (ex: «Buletin de analize ...»)
        _LINIE_NUME_CU_VARSTA = re.compile(
            r"^\w+\s+\w+.*\s+[MF]\s*,\s*\d+\s*(?:ani?|luni?)",
            re.IGNORECASE,
        )
        for linie in reversed(lines_before):
            if re.match(r"^[\d\(]", linie):
                continue
            if _LINIE_HEADER_NUME.match(linie):
                continue
            # Antet OCR: medic trimitător / doctor pe aceeași linie cu nume fals
            low_l = linie.lower().replace(" ", "")
            if "medicitrimitator" in low_l or "trimitator" in linie.lower():
                continue
            if _linie_este_exclusa(linie) and not _LINIE_NUME_CU_VARSTA.match(linie):
                continue
            # Strip sex/varsta si tot ce urmeaza (ex: «Buletin de analize CODE din DD.MM.YYYY»)
            clean = re.sub(r"\s+[FM]\s*,\s*\d+\s*(luni|ani).*", "", linie, flags=re.IGNORECASE).strip()
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
    # Cuvinte reale de analize medicale — daca oricare apare, NU e gunoi (in general)
    _CUVINTE_MEDICALE = re.compile(
        r"\b(hemoglobin[ăaäe]?|hemoglobina|hemoglobine?|hemoglobin|hematocrit|hematii|hematie|eritrocite?|leucocite?|trombocite?|neutrofile?|limfocite?|"
        r"monocite?|eozinofile?|bazofile?|creatinin(?:ă|a|e|i)?|glucoz[aeă]?|glicemi[aeă]?|colesterol|triglicerid|"
        r"bilirubin[ăaäe]?|feritin[ăaäe]?|fier|sodiu|potasiu|calciu|magneziu|fosfor|uree|acid|"
        r"proteina|albumin[ăaäe]?|microalbumin[aă]?|globulin[ăaäe]?|fibrinogen|vitamina|hormon|tsh|t3|t4|cortizol|"
        r"insulina|hemoglo|plachetar|eritrocitar|seric[ae]?|raport|urinar|sediment|sumar|"
        r"homocistein|complement|anticorp|imunoglobul|DAO|VSH|CRP|ALT|AST|GGT|"
        r"chem|mchc?|mcv|rdw|rdw[\-\s]?cv|vem|vtm|pdw|pdw[\-\s]?sd|pct|mpv|plcr|p[\-\s]?lcr|aslo|sideremie|estradiol|progesteron|fosfataz[ăaäe]?|"
        r"\bhem\b|"
        r"tsh|lh|fsh|ft4|free\s*t4|egfr|clearance|densitate|urobilinogen|pigment|"
        r"chlamydia|mycoplasma|ureaplasma|trachomatis|fier|feritin[ăaäe]?|magnezi|calciu|"
        r"transferina|bilirubin[ăaäe]?|amilaza|lipaza|fibrinogen|prolactina|testosteron|psa|"
        r"nitriti?|claritate|culoare|flora|mucus|epiteliale?|cetonici|proteine\s+urinare)\b",
        re.IGNORECASE,
    )
    are_cuvant_medical = bool(_CUVINTE_MEDICALE.search(linie))
    # pH (2 litere) — recunoaștere și după cod numerotat «1.1.1 pH …»
    if re.search(r"(?i)\bpH\b", linie):
        are_cuvant_medical = True
    # Rând «… valoare UM min - max» (MedLife): multe token-uri numerice trec pragul „silabe scurte".
    # NU apelăm _parse_oneline aici (în unele medii poate interacționa cu _este_linie_parametru la încărcare).
    m_tab = _RE_TABULAR_ROW_VAL_UM_INTERVAL.search(linie)
    if are_cuvant_medical and m_tab and re.search(r"[A-Za-zĂÂÎȘȚăâîșț]", linie[: m_tab.start()]):
        return False
    # Imparte in cuvinte (secvente ne-spatiu)
    cuvinte = linie.split()
    if len(cuvinte) < 4:
        if not are_cuvant_medical:
            return False
    # Numara cuvintele scurte (1-2 litere)
    scurte = sum(1 for c in cuvinte if len(_RE_STRIP_NON_LITERE.sub("", c)) <= 2)
    ratio_scurte = scurte / len(cuvinte) if cuvinte else 0
    # Artefact OCR: cuvant cu 3+ litere identice consecutive (ex: "RRR", "SSS") => gunoi sigur
    if re.search(r"\b([A-Za-z])\1{2,}\b", linie):
        return True
    # Linii medicale valide cu multe cifre/token-uri scurte (ex. «1.1.1 pH 5,0 5-7,5») — nu gunoi
    if are_cuvant_medical and (ratio_scurte <= 0.85 or re.search(r"(?i)\bpH\b", linie)):
        return False
    # Daca >75% silabe scurte => gunoi (fără cuvânt medical clar — altfel «Neutrofile % 56,3 % …» e respinsă)
    if ratio_scurte > 0.75 and not are_cuvant_medical:
        return True
    # Daca cuvant medical prezent => NU e gunoi
    if are_cuvant_medical:
        return False
    # Daca >55% sunt silabe scurte => gunoi OCR
    if ratio_scurte > 0.55:
        return True
    # Daca linia contine secvente de litere unice separate prin spatiu (tabel degradat)
    # ex: "i CR CE SERE De E Oa nea" - mai mult de 5 litere unice consecutive
    litere_unice = _RE_LITERA_UNICA.findall(linie)
    if len(litere_unice) >= 5 and len(litere_unice) / len(cuvinte) > 0.4:
        return True
    return False


# Substring-uri care indica gunoi OCR / footer - oriunde in linie
_GUNOI_SUBSTR = (
    ", Str.",  # adresă RO tip «ORAȘ, Str. NUME» (PDF/tabel; nu e parametru de laborator)
    "Răspuns rapid", "Răspuns lent", "Răspuns bifazic", "Răspuns absent",  # interpretare CRP
    "M, 1 an", "F, 28 ani", ", 1 an", ", 28 ani",  # sex + varsta
    "BOBEICA", "BCBEIEZA", "Testele cu marcajul", "Aceste rezultate pot fi folosite",
    "doza (0.5 g amoxicillin", "Pagina ", " din ",
    " spp -", "Enterobacteriaceae -", "micologic", "antibiograma", "nevoie Candida",
    "in 05.01.2026", "in 06.01.2026", "in 22.12.2025",  # disclaimer cu data
)


def _este_linie_parametru(linie: str) -> bool:
    if not linie:
        return False
    # Multe lab-uri pun metoda pe același rând (ex. „... -Ser - Spectrofotometrie / Chemiluminiscență")
    # — depășeau 150 caractere și erau ignorate complet → 0 analize extrase din PDF.
    _lim_lungime = 220
    if RE_BIOCLINICA_ONELINE.search(linie) or RE_BIOCLINICA_REF_SINGULAR.search(linie):
        _lim_lungime = 520
    if len(linie) > _lim_lungime:
        return False
    if _RE_DOAR_VALOARE_CA_PARAMETRU.match(linie.strip()):
        return False
    if _RE_METADATE_VARSTA_LINIE.search(linie) and len(linie) < 90:
        return False
    if _linie_este_exclusa(linie):
        return False
    if _RE_NUME_PACIENT_ALL_CAPS.match(linie.strip()):
        # „ACID URIC SERIC” (caps laborator) — nu e nume pacient
        if not _RE_ANALIZA_CAPS_EXCLUDE_NUME_PACIENT.search(linie.strip()):
            return False
    # Note clasificare diabetic (fragment OCR lângă prag 126 mg/dl)
    if re.match(r"(?i)^crescute\s+\d", linie.strip()):
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
    # Ignorăm sufixul «(referință: <30 …)» — altfel «VSH …: 20 mm/h (referință: <30)» e respinsă greșit.
    linie_fara_sufix_ref = linie
    m_suf_ref = re.search(r"\(\s*referin(?:ță|ta)\s*:", linie, re.IGNORECASE)
    if m_suf_ref:
        linie_fara_sufix_ref = linie[: m_suf_ref.start()].rstrip()
    if re.search(r":\s*[<>=≤≥]\s*\d", linie_fara_sufix_ref):
        return False
    # Linii cu text foarte scurt si ambiguu (< 3 litere) — exceptie pH (sumar urina), inclusiv după prefix 1.1.1
    _lit = _RE_STRIP_NON_ALPHA.sub("", linie)
    _dupa_prefix_nr = re.sub(r"^\d+(?:\.\d+)+\s+\*?\s*", "", linie).strip()
    if len(_lit) < 3 and not re.match(r"^pH\b", linie.strip(), re.IGNORECASE) and not re.match(
        r"^pH\b", _dupa_prefix_nr, re.IGNORECASE
    ):
        return False
    # Valoare izolată pe rând (ex: „9") — nu e analiză
    if re.match(r"^\d{1,5}\s*$", linie.strip()):
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
    if _linie_este_exclusa(param_part):
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


def _extrage_valoare_text_din_fragment_dreapta(right: str) -> Optional[str]:
    """
    Din partea dreaptă a «Analiză = …» extrage rezultatul text (Negativ, Normal, …),
    după ce taie UM și sufixe «Normal» repetate (ex: «Negativ mg/dL Normal»).
    """
    s = (right or "").strip()
    for _ in range(4):
        s2 = re.sub(r"\s+Normal\s*$", "", s, flags=re.IGNORECASE).strip()
        s2 = re.sub(
            r"\s*(?:mg/dL|mg/dl|mmol/L|g/L|UI/L|U/L|%)\s*$",
            "",
            s2,
            flags=re.IGNORECASE,
        ).strip()
        if s2 == s:
            break
        s = s2
    low = s.lower()
    if re.search(r"\bnedetectabil", low):
        return "Nedetectabil"
    if re.search(r"\bnedecelabil", low):
        return "Nedecelabil"
    if re.search(r"\bnegativ", low):
        return "Negativ"
    if re.search(r"\bpozitiv", low):
        return "Pozitiv"
    if re.search(r"\babsent", low):
        return "Absent"
    if re.search(r"\bprezent", low):
        return "Prezent"
    if re.search(r"\breactiv", low):
        return "Reactiv"
    if re.search(r"\bsensibil\b", low):
        return "Sensibil"
    if re.search(r"\brezistent\b", low):
        return "Rezistent"
    if re.search(r"\bintermedi(?:ar|u)\b", low):
        return "Intermediar"
    if re.search(r"^normal\s*$|^\s*normal\s+", low) or low == "normal":
        return "Normal"
    if re.search(r"\blimpede\b", low):
        return "Limpede"
    if re.search(r"\btulbure\b", low):
        return "Tulbure"
    if re.search(r"\burme\b", low):
        return "Urme"
    if re.search(r"\brar[ăae]?\b", low):
        return "Rară"
    return None


def _parse_linie_egal_rezultat(linie: str) -> Optional[RezultatParsat]:
    """
    Format «Glucoză = Negativ mg/dL Normal» sau «Parametru = 92 mg/dL».
    Separă denumirea analizei de rezultat (text sau numeric).
    """
    if "=" not in linie:
        return None
    linie = linie.strip()
    # Nu trata «<=» / «>=» ca separator «=» (ex. microalbumină «<=10 mg/L»)
    m = re.match(r"^([^=\n]{2,160}?)(?<!<|>)\s*=\s*(.+)$", linie)
    if not m:
        return None
    left = m.group(1).strip()
    # Trailing pipe (SANTE VIE: "Rata filtrarii glomerulare =")
    left = re.sub(r'\s*\|+\s*$', '', left).strip()
    right = m.group(2).strip()
    if len(left) < 2:
        return None
    if re.fullmatch(r"[kKcC]\s*", left):
        return None
    if _linie_este_exclusa(left):
        return None
    right_lc = right.lower()
    has_lab_semantic = bool(
        re.search(
            r"\b(negativ|pozitiv|absent|prezent|normal|nedecel|nedetect|reactiv|rar|limpede|tulbure|urme|"
            r"sensibil|rezistent|intermedi(?:ar|u))\b",
            right_lc,
        )
    )
    # Format special: "1,70 <30 mg/g" (valoare + comparator_limita + unitate)
    # Ex: "Raport albumina creatinina = 1,70 <30 mg/g"
    m_val_limit = re.search(
        r"^(\d+[.,]\d+|\d+)\s+([<>≤≥]=?)\s*(\d+[.,]?\d*)\s+([a-zA-Z/%µμg²³·\/]+)",
        right.strip(),
    )
    if m_val_limit:
        valoare_raw = m_val_limit.group(1)
        op = m_val_limit.group(2)
        lim_raw = m_val_limit.group(3)
        unitate_raw = m_val_limit.group(4).strip()
        val_v = _parse_european_number(valoare_raw)
        lim_v = _parse_european_number(lim_raw)
        if val_v is not None and lim_v is not None:
            int_min = 0.0 if op in ("<", "<=", "≤") else lim_v
            int_max = lim_v if op in ("<", "<=", "≤") else lim_v * 10
            return RezultatParsat(
                denumire_raw=_curata_denumire_rezultat(left, None) or left,
                valoare=val_v,
                unitate=unitate_raw or None,
                interval_min=int_min,
                interval_max=int_max,
            )

    m_num = re.search(
        r"(?<!\S)(\d+[.,]\d+|\d+)\s+([a-zA-Z/%µμg·²³'\/][a-zA-Z0-9/%µμg·²³'\/\*\.]*)",
        right,
    )
    if not has_lab_semantic and not m_num:
        return None
    vt = _extrage_valoare_text_din_fragment_dreapta(right)
    if vt:
        d = _curata_denumire_rezultat(left, vt)
        return RezultatParsat(
            denumire_raw=d or left,
            valoare=None,
            valoare_text=vt,
            unitate=None,
        )
    if m_num:
        valoare = _parse_european_number(m_num.group(1))
        if valoare is None:
            try:
                valoare = float(m_num.group(1).replace(",", "."))
            except ValueError:
                return None
        unitate = (m_num.group(2) or "").strip() or None
        # Extrage intervalul din restul dupa valoare+unitate
        rest_num = right[m_num.end():]
        m_int = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)", rest_num)
        int_min = int_max = None
        if m_int:
            int_min = _parse_european_number(m_int.group(1))
            int_max = _parse_european_number(m_int.group(2))
            if int_min is not None and int_max is not None and int_min >= int_max:
                int_min = int_max = None
        den = _curata_denumire_rezultat(left, None) or left
        # Curatam trailing "=" din denumire (ex: "Hemoglobina(HGB) =")
        den = re.sub(r'\s*=\s*$', '', den).strip()
        valoare = _corecteaza_decimal_pierdut(valoare, int_min, int_max, den)
        return RezultatParsat(
            denumire_raw=den,
            valoare=valoare,
            unitate=unitate,
            interval_min=int_min,
            interval_max=int_max,
        )
    return None


def _categorie_inferata_din_denumire(
    denumire_raw: str, categorie_pdf: Optional[str]
) -> Optional[str]:
    """
    Completează categoria din PDF când OCR/antet lipsesc: microbiologie, sediment urină.
    """
    d = (denumire_raw or "").strip()
    if not d:
        return categorie_pdf
    low = d.lower()
    if re.search(
        r"\b(staphylococcus|streptococcus|haemophilus|enterobacteriaceae|enterobacter\s|moraxella|"
        r"candida\s|clostridium|klebsiella|escherichia|pseudomonas|acinetobacter|neisseria|salmonella|"
        r"serratia|proteus|enterococcus|listeria|legionella|mycobacterium|trichomonas|chlamydia|mycoplasma|"
        r"ureaplasma|bacillus|aspergillus|cryptococcus|bacteroides|hemocult|urocult|antibiogram|"
        r"toxina\s+[ab]\b|toxina\s+clostridium|\bgdh\b|screening\s+mrsa|difficile)\b",
        low,
    ):
        return "Microbiologie"
    ur_sed = (
        "celule epiteliale plate",
        "epiteliale plate",
        "celule epiteliale tranzi",
        "epiteliale tranzi",
        "alte cristale",
    )
    if any(k in low for k in ur_sed):
        if categorie_pdf == "Examen urina":
            return categorie_pdf
        return categorie_pdf or "Examen urina"
    if "glucoz" in low and ("urin" in low or "urinar" in low):
        return categorie_pdf or "Examen urina"
    if (
        categorie_pdf is None
        and "glucoz" in low
        and "urin" not in low
        and "urinar" not in low
    ):
        return "Biochimie"
    return categorie_pdf


# Liniuță / minus Unicode (Capatan / Gaman / rapoarte digitale — evită `[]` cu `-` ambiguu)
_RE_DASH_UCR = r"(?:-|–|—|\u2010|\u2011|\u2012|\u2013|\u2014|\u2015)"


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

    # MedLife: «Rezultat cantitativ: Bacteriurie <1000 UFC/ml …» — nu extrage 1000 ca valoare principală
    if re.search(r"(?i)rezultat\s+cantitativ", linie) and re.search(r"(?i)bacteriurie", linie):
        return RezultatParsat(
            denumire_raw="Urocultură",
            valoare=None,
            valoare_text=re.sub(r"\s+", " ", linie.strip())[:4000],
            unitate=None,
            rezultat_tip="microbiology",
        )

    if re.match(r"(?i)^organisme\s+absente\s*:", linie):
        tail = linie.split(":", 1)[1].strip() if ":" in linie else ""
        return RezultatParsat(
            denumire_raw="Organisme absente",
            valoare=None,
            valoare_text=re.sub(r"\s+", " ", tail)[:4000] if tail else None,
            unitate=None,
            rezultat_tip="microbiology",
        )

    m_res = re.match(r"(?i)^rezultat\s*:\s*(.+)$", linie)
    if m_res and len(m_res.group(1).strip()) > 4:
        tx = re.sub(r"\s+", " ", m_res.group(1).strip())
        return RezultatParsat(
            denumire_raw="Rezultat urocultură",
            valoare=None,
            valoare_text=tx[:4000],
            unitate=None,
            rezultat_tip="microbiology",
        )
    m_alt_org = re.match(r"(?i)^(alte\s+organisme\s+absente)\s*:\s*(.+)$", linie)
    if m_alt_org and len(m_alt_org.group(2).strip()) > 3:
        return RezultatParsat(
            denumire_raw=m_alt_org.group(1).strip(),
            valoare=None,
            valoare_text=re.sub(r"\s+", " ", m_alt_org.group(2).strip())[:4000],
            unitate=None,
            rezultat_tip="microbiology",
        )

    r_egal = _parse_linie_egal_rezultat(linie)
    if r_egal is not None:
        return r_egal

    # Elimina prefix numeric de linie (ex: "9.3 Alfa2-globuline%", "1.2.1 Celule" -> "Celule")
    linie = re.sub(r'^\d+(?:\.\d+)+\s+\*?\s*', '', linie).strip()
    if not linie:
        return None

    # Capatan sumar urină (înainte de _strip_suffix… care taie «… Normal» de la sfârșit)
    m_cap_dd = re.match(
        r"(?i)^(?P<name>[A-Za-zĂÂÎȘȚăâîșț][\w\s\-/\.\(\)]{0,78}?)\s+-\s+-\s*\(\s*(?P<v>[^)]+)\)\s*$",
        linie,
    )
    if m_cap_dd:
        nm = m_cap_dd.group("name").strip()
        vt = re.sub(r"\s+", " ", m_cap_dd.group("v").strip())
        if nm and len(nm) >= 2 and len(nm) < 85:
            return RezultatParsat(denumire_raw=nm, valoare=None, valoare_text=vt, unitate=None)

    m_cap_d1 = re.match(
        r"(?i)^(?P<name>[A-Za-zĂÂÎȘȚăâîșț][\w\s\-/\.\(\)]{0,78}?)\s+" + _RE_DASH_UCR + r"\s+(?P<v>Normal|Negativ|Absente?|Absent[aă]?|Absen[țt]i|Prezent[aă]?|Rar(?:[aă]|e|i)?|Frecvente?|Nu\s+se\s+observ[aă]?|Negative)\s*$",
        linie,
    )
    if m_cap_d1:
        nm = m_cap_d1.group("name").strip()
        vt = m_cap_d1.group("v").strip()
        if nm and len(nm) >= 2 and len(nm) < 85:
            return RezultatParsat(denumire_raw=nm, valoare=None, valoare_text=vt, unitate=None)

    m_cap_rel = re.match(
        r"(?i)^(?P<name>.+?)\s+(Relativ\s+frecvente)\s+(Rare|rar[aă]?)(?:\s*\([^)]{1,120}\))?\s*$",
        linie.strip(),
    )
    if m_cap_rel:
        nm = m_cap_rel.group("name").strip().rstrip(",.")
        if nm and len(nm) >= 2 and len(nm) < 90 and not re.match(
            r"(?i)^relativ\s+frecvente\b",
            nm,
        ):
            vt = f"{m_cap_rel.group(2)} {m_cap_rel.group(3)}".strip()
            return RezultatParsat(denumire_raw=nm, valoare=None, valoare_text=vt, unitate=None)

    linie = _strip_suffix_interpretare_clasificare(linie)
    if not linie:
        return None

    # Regina Maria / Unirea: «pH urinar 6 [5 - 7]», «Densitate urinara 1008 [1010 - 1030]»
    # (nume înainte de valoare, interval în paranteze pătrate)
    m_nm_br = re.match(
        r"^(.+?)\s+(\d+[.,]?\d*)\s+\[\s*([\d.,]+)\s*[-–−]\s*([\d.,]+)\s*\]\s*$",
        linie.strip(),
    )
    if m_nm_br:
        lo_nb = _parse_european_number(m_nm_br.group(3))
        hi_nb = _parse_european_number(m_nm_br.group(4))
        val_nb = _parse_european_number(m_nm_br.group(2))
        if val_nb is not None and lo_nb is not None and hi_nb is not None and lo_nb < hi_nb:
            den_nb = m_nm_br.group(1).strip()
            if den_nb and len(den_nb) >= 2 and not re.match(r"^\d", den_nb):
                fl_nb = None
                if val_nb < lo_nb:
                    fl_nb = "L"
                elif val_nb > hi_nb:
                    fl_nb = "H"
                return RezultatParsat(
                    denumire_raw=den_nb,
                    valoare=val_nb,
                    unitate=None,
                    interval_min=lo_nb,
                    interval_max=hi_nb,
                    flag=fl_nb,
                )

    # Regina Maria / Unirea (PDF tabel): valoare numerică înaintea numelui, interval în paranteze pătrate
    # ex: «6 pH urinar [5 - 7]», «1008 Densitate urinara [1010 - 1030]»
    m_vp_br = re.match(
        r"^(\d+[.,]?\d*)\s+(.+?)\s+\[\s*([\d.,]+)\s*[-–−]\s*([\d.,]+)\s*\]\s*$",
        linie.strip(),
    )
    if m_vp_br:
        val_vp = _parse_european_number(m_vp_br.group(1))
        lo_vp = _parse_european_number(m_vp_br.group(3))
        hi_vp = _parse_european_number(m_vp_br.group(4))
        if val_vp is not None and lo_vp is not None and hi_vp is not None and lo_vp < hi_vp:
            den_vp = m_vp_br.group(2).strip()
            if den_vp and len(den_vp) >= 2:
                fl_vp = None
                if val_vp < lo_vp:
                    fl_vp = "L"
                elif val_vp > hi_vp:
                    fl_vp = "H"
                return RezultatParsat(
                    denumire_raw=den_vp,
                    valoare=val_vp,
                    unitate=None,
                    interval_min=lo_vp,
                    interval_max=hi_vp,
                    flag=fl_vp,
                )

    # Sumar urină: «Mucus … Prezent … Absent, Rar» — altfel regex-ul de la sfârșit prinde «Rar» ca valoare
    if re.match(r"(?i)^mucus\b", linie):
        if re.search(r"(?i)(?<![\w-])prezent[aă]?(?![\w-])", linie):
            return RezultatParsat(
                denumire_raw="Mucus",
                valoare=None,
                valoare_text="Prezent",
                unitate=None,
            )
        if re.search(r"(?i)(?<![\w-])absent[aă]?(?![\w-])", linie) and not re.search(
            r"(?i)\bprezent",
            linie,
        ):
            return RezultatParsat(
                denumire_raw="Mucus",
                valoare=None,
                valoare_text="Absent",
                unitate=None,
            )
        if re.search(r"(?i)(?<![\w-])rar[aă]?(?![\w-])", linie) and not re.search(
            r"(?i)\bprezent",
            linie,
        ):
            return RezultatParsat(
                denumire_raw="Mucus",
                valoare=None,
                valoare_text="Rar",
                unitate=None,
            )

    # Sumar urină: «Culoare Galben deschis Galben, Galben deschis» / «Claritate …» — rezultat + referință cu termen duplicat
    m_vis = re.match(
        r"(?i)^(culoare|claritate)\*?\s+" + _RE_DASH_UCR + r"\s+(.+)$",
        linie.strip(),
    )
    if m_vis:
        key = m_vis.group(1).strip().capitalize()
        rest = m_vis.group(2).strip()
        if "," in rest:
            left, ref = rest.split(",", 1)
            left = left.strip()
            ref_first = ref.strip().split(",")[0].strip().split()
            first_ref = ref_first[0] if ref_first else ""
            words = left.split()
            if (
                first_ref
                and words
                and words[-1].lower().rstrip(".,;:") == first_ref.lower().rstrip(".,;:")
                and len(words) > 1
            ):
                left = " ".join(words[:-1])
        else:
            left = rest
        ws = left.split()
        if len(ws) >= 2 and ws[-1].lower().rstrip(".,;:") == ws[-2].lower().rstrip(".,;:"):
            left = " ".join(ws[:-1])
        if left:
            return RezultatParsat(
                denumire_raw=key,
                valoare=None,
                valoare_text=left,
                unitate=None,
            )

    # Gaman / sediment: «Celule epiteliale plate – Foarte rare» (o singură apariție)
    m_ep_plate_dash = re.match(
        r"(?i)^(?P<name>Celule\s+epiteliale\s+plate)\s+" + _RE_DASH_UCR + r"\s+(Foarte\s+rare)\s*$",
        linie.strip(),
    )
    if m_ep_plate_dash:
        return RezultatParsat(
            denumire_raw="Celule epiteliale plate",
            valoare=None,
            valoare_text="Foarte rare",
            unitate=None,
        )
    m_leuco_sed_dash = re.match(
        r"(?i)^(?P<name>Leucocite\s+sediment)\s+" + _RE_DASH_UCR + r"\s+(Foarte\s+rare)\s*$",
        linie.strip(),
    )
    if m_leuco_sed_dash:
        return RezultatParsat(
            denumire_raw="Leucocite sediment",
            valoare=None,
            valoare_text="Foarte rare",
            unitate=None,
        )

    # Sumar urină: «Celule epiteliale plate Foarte rare Foarte rare, Rare»
    m_dup_foarte = re.match(
        r"(?i)^(?P<name>.+?)\s+(Foarte\s+rare)\s+(Foarte\s+rare)\b\s*(?:,.*)?$",
        linie.strip(),
    )
    if m_dup_foarte:
        name_fr = m_dup_foarte.group("name").strip().rstrip(",.")
        if name_fr and len(name_fr) >= 2:
            return RezultatParsat(
                denumire_raw=name_fr,
                valoare=None,
                valoare_text="Foarte rare",
                unitate=None,
            )

    # Sumar urină: «… Normal Normal, <25 mg/dl» / «Absente Absente» — nu interpreta pragul ca valoare
    m_dup_txt = re.match(
        r"(?i)^(?P<name>.+?)\s+"
        r"(?P<v>Normal|Negativ|Absente?|Absent[aă]?|Absenti|Prezent[aă]?)\s+(?P=v)\b"
        r"\s*(?:,.*)?$",
        linie,
    )
    if m_dup_txt:
        name_dt = m_dup_txt.group("name").strip().rstrip(",.")
        vt = m_dup_txt.group("v")
        if name_dt and len(name_dt) >= 2:
            return RezultatParsat(
                denumire_raw=name_dt,
                valoare=None,
                valoare_text=vt,
                unitate=None,
            )

    # Urocultură cu rezultat descriptiv (MedLife/TEO) — nu extrage 100.000 UFC ca valoare principală.
    if re.search(r"(?i)urocultur[aă]\s*:", linie):
        tail = linie[re.search(r"(?i)urocultur[aă]\s*:", linie).end() :].strip()
        if re.search(r"(?i)pozitiv|negativ|absent|prezent", tail) and not re.match(
            r"^\s*[\d<>≤≥]", tail
        ):
            return RezultatParsat(
                denumire_raw="Urocultură",
                valoare=None,
                valoare_text=tail[:4000],
                unitate=None,
                rezultat_tip="microbiology",
            )

    # După UM, referință «< N» la sfârșit (ex. microalbumină «mg/L < 10») — nu e valoare separată
    if re.search(r"(?i)mg/dL|mg/L|g/dL|g/L|mmol/L", linie):
        linie = re.sub(r"\s+<\s*\d[\d\.,]*\s*$", "", linie).strip()

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
    # Unități MedLife: *10^6/µL; Sante Vie: 10^9/L; valori «< 73» cu comparator opțional; «<=10 mg/L»
    m_val = re.search(
        r"(?<!\S)(?:(?:<=|>=)|[<>≤≥]\s*)?(\d+[.,]\d+|\d+)\s+"
        r"((?:" + _RE_UM_X10_SLASH + r")|\*[\w/.^µμ·]+|10\^[\d]+/[a-zA-ZµμL]+|[a-zA-Z%µμg·²³'\/][a-zA-Z0-9%µμg·²³'\/\*\^\.·,]*)"
        r"(?:\s+|$)",
        linie,
    )
    if not m_val:
        # Incearca sa gaseasca o valoare TEXT (negativ, pozitiv, absent etc.)
        # Format: "NUME ANALIZA [,] VALOARE_TEXT"
        m_text = re.search(
            r"[\s,\.]+(_VALOARE_TEXT_)$".replace(
                "_VALOARE_TEXT_",
                r"(?:negativ[ae]?|pozitiv[ae]?|absent[ae]?|absen[țt]i|prezent[ae]?|rar(?:[ae]|i)?|frecvente?|"
                r"normal[ae]?|crescut[ae]?|scazut[ae]?|reactiv[ae]?|nedecelabil[ae]?|"
                r"nedetectabil[ae]?|nu\s+se\s+observ[aă]?|"
                r"epitelii\s+\w+|leucocite\s+\w+|hematii\s+\w+|"
                r"cilindri\s+\w+|cristale\s+\w+|bacterii\s+\w+|mucus\s+\w+|"
                r"foarte\s+rare|"
                r"galben[ae]?|incolor[ae]?|tulbure|limpede|clar[ae]?|"
                r"urme|trace[s]?|\+{1,4}[-+]?\d*|\+[-±]?\b|"
                r"<=?\s*\d[\d\.,]*(?:\s*mg/L)?|"
                r"\<\s*\d[\d\.,]*\s*\w*|\>\s*\d[\d\.,]*\s*\w*)"
            ),
            linie,
            re.IGNORECASE,
        )
        if not m_text:
            # Format pdfplumber: "Denumire ValoareText UM" (UM dupa valoarea text)
            # ex: "Leucocite +- leu/ul", "Eritrocite Negativ ery/ul", "Glucoza +4 mg/dL"
            _VT_PAT = (
                r"(?:negativ[ae]?|pozitiv[ae]?|absent[ae]?|absen[țt]i|prezent[ae]?|rar[ae]?|"
                r"normal[ae]?|crescut[ae]?|scazut[ae]?|reactiv[ae]?|nedecelabil[ae]?|"
                r"nedetectabil[ae]?|\+{1,4}[-+]?\d*|\+[-±]?\b|"
                r"<=?\s*\d[\d\.,]*|"
                r"\<\s*\d[\d\.,]*|\>\s*\d[\d\.,]*)"
            )
            _UM_PAT = r"(?:[a-zA-Z%µμ][a-zA-Z0-9%µμ·²³'\/\.\^]{0,15})"
            m_text_um = re.search(
                r"[\s,\.]+(" + _VT_PAT + r")\s+(" + _UM_PAT + r")\s*$",
                linie,
                re.IGNORECASE,
            )
            if m_text_um:
                name = linie[:m_text_um.start()].strip().strip(",.")
                name = re.sub(r'^["\'\*%\s]+', '', name).strip()
                if name and len(name) >= 2 and not re.match(r'^\d+[.,]?\d*\s*$', name):
                    return RezultatParsat(
                        denumire_raw=name,
                        valoare=None,
                        valoare_text=m_text_um.group(1).strip(),
                        unitate=m_text_um.group(2).strip(),
                    )
            # Fallback: "Denumire Valoare" fara unitate (ex: pH 5,0, Densitate 1.023)
            # Evită «pH 5,0 5-7,5» → valoare 7,5: taie intervalul de referință de la sfârșit.
            linie_num = linie
            trail_imin: Optional[float] = None
            trail_imax: Optional[float] = None
            for _ in range(3):
                rest_i, lo_i, hi_i = _strip_trailing_interval_range(linie_num)
                if lo_i is None:
                    break
                linie_num = rest_i
                trail_imin, trail_imax = lo_i, hi_i
            m_num_end = re.search(r"(?<!\w)([<>≤≥]?\s*\d+[.,]\d+|\d{2,})\s*$", linie_num)
            if m_num_end:
                name_cand = linie_num[:m_num_end.start()].strip()
                name_cand = re.sub(r'^["\'\*%\s]+', '', name_cand).strip()
                if (name_cand and len(name_cand) >= 2 and not re.match(r"^\d", name_cand)
                        and not re.search(r"\d+[.,]\d+|\d{2,}", name_cand)):
                    val = _parse_european_number(m_num_end.group(1).replace(' ', ''))
                    if val is not None:
                        return RezultatParsat(
                            denumire_raw=name_cand,
                            valoare=val,
                            unitate=None,
                            interval_min=trail_imin,
                            interval_max=trail_imax,
                        )
            return None
        name = linie[:m_text.start()].strip().strip(",.")
        name = re.sub(r'^["\'\*%\s]+', '', name).strip()
        if not name or len(name) < 2 or re.match(r'^\d+[.,]?\d*\s*$', name):
            return None
        valoare_text = m_text.group(1).strip()
        # «Alte cristale negativ» — regex-ul valorii text prinde doar «cristale negativ» în dreapta.
        if name.strip().lower() == "alte" and valoare_text:
            m_fix_alte = re.match(
                r"(?i)^(cristale(?:\s+[\w\u0103\u00e2\u00ee\u0219\u021b\.,\-\(\)]+)*)\s+"
                r"(negativ[ae]?|pozitiv[ae]?|absent[ae]?|prezent[ae]?|normal[ae]?|rar[ae]?|"
                r"frecvent[ae]?|urme|foarte\s+rare)\s*$",
                valoare_text.strip(),
            )
            if m_fix_alte:
                name = f"{name.strip()} {m_fix_alte.group(1).strip()}"
                valoare_text = m_fix_alte.group(2).strip()
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

    # Curata artefacte OCR din nume (ghilimele, asteriscuri, pipe la inceput/sfarsit)
    name = re.sub(r'^["\'\*%\s]+', '', name).strip()
    # Trailing pipe (separator SANTE VIE: "Colesterol seric total | 488 mg/dL" -> name="Colesterol seric total |")
    name = re.sub(r'\s*\|+\s*$', '', name).strip()
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
    # Referinta singulara fara paranteze: "<56 U/L" sau ">5" sau "≤ 100"
    if interval_min is None and interval_max is None:
        m_ref_sing = re.search(r"([<>≤≥]|<=|>=)\s*([\d.,]+)", rest)
        if m_ref_sing:
            op = m_ref_sing.group(1)
            ref_val = _parse_european_number(m_ref_sing.group(2))
            if ref_val is not None:
                if op in ("<", "<=", "≤"):
                    interval_min = 0.0
                    interval_max = ref_val
                elif op in (">", ">=", "≥"):
                    # Prag inferior de normalitate (ex. HDL ≥ 60) — fără plafon artificial (60–600).
                    interval_min = ref_val
                    interval_max = None

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
    elif valoare is not None and interval_min is not None and interval_max is None:
        if valoare < interval_min:
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
    ("vem", 120.0),      # MCV tipic 80-100 fL (Bioclinica/Regina Maria)
    ("mcv", 120.0),      # MCV tipic 80-100 fL (Sante Vie / alte lab)
    ("volum mediu erit", 120.0),  # Volum mediu eritrocitar (MCV)
    ("mch", 40.0),       # MCH tipic 27-33 pg
    ("mchc", 40.0),      # MCHC tipic 32-36 g/dL
    ("hemoglobin", 25.0),  # Hemoglobina tipic 12-17 g/dL; 168 -> 16.8
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

    Protectie: daca valoarea are deja zecimale (ex 14.89) si intervalul pare corupt
    (interval_max > 10 * valoare), nu modifica — intervalul e cel eronat, nu valoarea.
    """
    # Strategie 1: cu interval
    if interval_max is not None and interval_max > 0:
        # Nu corecta valori cu referinta mica (CRP ≤0.33, hormoni, etc.)
        # Valorile clinice mari (ex. CRP 2.26 cu ref ≤0.33) sunt legitime, nu erori OCR.
        if interval_max < 5.0:
            return valoare
        # Daca valoarea are deja zecimale si intervalul e suspect de mare, intervalul e cel corupt
        has_decimals = (valoare != int(valoare)) if valoare is not None else False
        if has_decimals and interval_max > valoare * 8 and valoare > 0:
            return valoare  # interval corupt de OCR, valoarea e OK
        if valoare > 10 * interval_max:
            v10 = valoare / 10
            if v10 <= 2 * interval_max:
                return v10
            v100 = valoare / 100
            if v100 <= 2 * interval_max:
                return v100
        # Cazul: 121 cu interval [10.7, 14.1] → 121/10 = 12.1 e in interval
        # OCR a omis punctul zecimal (12.1 → 121)
        if valoare > interval_max * 5:
            v10 = valoare / 10
            if interval_min is not None and interval_min <= v10 <= interval_max * 1.5:
                return v10
            elif interval_min is None and v10 <= interval_max * 1.5:
                return v10
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
    r"^([\d.,]+)\s+((?:" + _RE_UM_X10_SLASH + r")|\*[\w/.^µμ³·]+|[a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
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

# Format Gaman / rapoarte digitale: «Param – valoare UM» + linia următoare «Interval: min – max»
# (fără paranteze la interval — altfel _combina_linii_bioclinica Caz 1a nu lipește)
# Liniuță tipografică / minus (evită `[]` cu `-` ambiguu între coduri Unicode)
_RE_GAMAN_PARAM_VAL_UM = re.compile(
    r"^(.{2,220}?)\s+" + _RE_DASH_UCR + r"\s+"
    r"((?:[<>≤≥]\s*)?)(\d+[.,]\d+|\d+)(?:\s+(.+))?$",
    re.UNICODE,
)
_RE_INTERVAL_LABEL_LINIE = re.compile(
    # «Interval menopauză: <37 – 102.76» sau «Interval: 5 – 34»
    r"^\s*Interval(?:\s+[^:]+:\s*|\s*:\s*)(?:[<>≤≥]{1,2}\s*)?([\d.,]+)\s*" + _RE_DASH_UCR + r"\s+([\d.,]+)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_LABEL_SINGULAR_TXT = re.compile(
    r"^\s*Interval\s*:\s*((?:<=|>=)|[<>≤≥])\s*([\d.,]+)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_LABEL_GE_NUM = re.compile(
    r"^\s*Interval\s*:\s*(?:≥|>=|⩾)\s*([\d.,]+)\s*$",
    re.IGNORECASE,
)

# OCR citeste √ ca "V" — detecteaza linie Gaman cu valoare (numerica sau text) dupa dash
_RE_GAMAN_DASH_ANY_VALUE = re.compile(
    _RE_DASH_UCR + r"\s*"
    r"(?:\d|Normal\b|Negativ\b|Absent\b|Prezent\b|Rar(?:[ae]|i)?\b|Frecvente?\b|Nu\s+se\s+observ)",
    re.IGNORECASE,
)

# Format pdfplumber formula leucocitara: "Param NUM1 UM1 NUM2 % (INT1)suffix" + urmatoarea "(INT2)%"
# Unitatea poate fi /mm3, /mm³, etc.
_RE_FORMULA_PDFPLUMBER = re.compile(
    r"^([A-Za-zăâîșțĂÂÎȘȚ]+)\s+([\d.,]+)\s*([\/\w³·0-9]+?)\s+([\d.,]+)\s*%\s+\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)


# Sufixe „Data recoltării … DD.MM.YYYY" sau doar dată la sfârșit (Bioclinica, Synevo, Capatan etc.)
_RE_TRAILING_DATE_LABELED = re.compile(
    r"\s+(?:Data\s+(?:recolt(?:are)?|lucr(?:at)?|tipar|generat)[a-zăâîșț]*|Recoltat|Lucrat)\s*:?\s*"
    r"\d{1,2}\.\d{1,2}\.\d{4}(?:\s+\d{1,2}:\d{2})?\s*$",
    re.IGNORECASE,
)
_RE_TRAILING_DATE_EOL = re.compile(r"\s+\d{1,2}\.\d{2}\.\d{4}(?:\s+\d{1,2}:\d{2})?\s*$")


def _strip_suffix_interpretare_clasificare(linie: str) -> str:
    """
    Elimină sufixe de tip lipidogramă / glicemie: «> 60 Normal», «<150 mg/dL risc scăzut»,
    «(40-60) Optim» etc., astfel încât rămâne analiză + valoare (+ eventual interval în paranteze).
    Fără asta, _parse_oneline respingea întreaga linie ca „clasificare" și pierdeau zeci de analize.
    """
    if not linie or len(linie) < 6:
        return linie
    s = linie.strip()
    # După «)» care închide intervalul de referință, text de interpretare
    if ")" in s:
        idx = s.rfind(")")
        tail = s[idx + 1 :].strip()
        if tail and len(tail) < 120 and re.match(
            r"^(?:[<>≤≥]\s*[\d.,]+\s*(?:mg/dL|mmol/L|g/L|U/L|%|UI/L|ng/mL)?\s*)?"
            r"(?:Normal|Optim|Borderline|scazut|scăzut|crescut|Nivel|risc|acceptable|deficit|toxic|"
            r"diabet|patolog|referinta|recomandat|De\s+[A-Z])\b",
            tail,
            re.IGNORECASE,
        ):
            s = s[: idx + 1].rstrip()
    # Comparator + prag + (opțional UM) + cuvânt cheie interpretare
    for _ in range(4):
        m = re.search(
            r"\s+[<>≤≥]\s*[\d.,]+\s*(?:mg/dL|mmol/L|g/L|U/L|UI/L|%|ng/mL|µg/dL|µg/L)?\s*"
            r"(?:Normal|Optim|Borderline|scazut|scăzut|crescut|risc|acceptable|deficit|toxic|"
            r"diabet|patolog|referinta|recomandat|De\s+[A-Z])\b.*$",
            s,
            re.IGNORECASE,
        )
        if not m:
            break
        s = s[: m.start()].rstrip()
    # Doar cuvânt de clasificare la sfârșit (ex: «... mg/dL Normal»)
    m2 = re.search(
        r"\s+(?:Normal|Optim|Borderline|scazut[ăa]?|crescut[ăe]?|Nivel\s+toxic|Acceptabil)\s*$",
        s,
        re.IGNORECASE,
    )
    if m2:
        s = s[: m2.start()].rstrip()
    # MedLife PDR: "Nivel de risc ...", "Nivel de atentie ...", "Nivel convenabil ..." ca sufix inline
    # ex: "HDL Colesterol 60.3 mg/dl Nivel de risc scazut : >= 60 mg/dl" → "HDL Colesterol 60.3 mg/dl"
    m_nivel = re.search(
        r"\s+Nivel\s+(?:de\s+risc|de\s+atenti[ei]|convenabil|optim)\b.*$",
        s,
        re.IGNORECASE,
    )
    if m_nivel:
        s = s[: m_nivel.start()].rstrip()
    # OCR: resturi scurte după valoare («enma V», «ME)»)
    s = re.sub(r"\s+[A-Za-z]{2,5}\s+[Vv]\s*$", "", s).strip()
    s = re.sub(r"\s+ME\)\s*$", "", s, flags=re.IGNORECASE).strip()
    return s


_RE_MEDLIFE_METHOD_LINE = re.compile(
    r"(?i)^(Ser,|Plasma\b|Urin[aă]\b|Whole\s+blood\b|"
    r".{0,40}\bmetoda\b|CMIA\b|ECLIA\b|spectrofotometric)",
)


def _line_has_extractable_value_row(s: str) -> bool:
    """True dacă linia arată ca rând de tabel cu valoare numerică (MedLife / generic)."""
    t = (s or "").strip()
    if not t:
        return False
    if RE_VALOARE_LINIE.match(t) or RE_VALOARE_REF_SINGULAR.match(t):
        return True
    if RE_VALOARE_LINIE_DASH.match(t):
        return True
    if RE_VALOARE_PARTIAL.match(t):
        return True
    if RE_VALOARE_SLASH_UNIT.match(t):
        return True
    if RE_BIOCLINICA_ONELINE.search(t) or RE_BIOCLINICA_REF_SINGULAR.search(t):
        return True
    # «Parametru valoare UM min - max» pe aceeași linie (OCR uneori lipește tot rândul)
    if _RE_TABULAR_ROW_VAL_UM_INTERVAL.search(t):
        return True
    # MedLife cantitativ / imunologie: «<20 IU/mL», «≤ 4,2 ulU/mL» (fără cifră la începutul liniei)
    if re.search(
        r"(?:^|(?<=\s))(?:[<>≤≥]\s*)(?:\d+[.,]\d+|\d+)\s+"
        r"(?:IU/mL|UI/mL|ulU/mL|µIU/mL|mIU/L|mg/dL|g/dL|U/L|ng/dL|ng/mL|mmol/L|pmol/L|nmol/L|%|fL|pg)\b",
        t,
        re.I,
    ):
        return True
    return False


def _looks_like_medlife_test_only_line(s: str) -> bool:
    """Linia pare denumire analiză fără valoare pe același rând (MedLife cu metoda pe rând separat)."""
    t = (s or "").strip()
    if not t or len(t) > 180:
        return False
    # Rând «Interval: …» (Gaman / rapoarte digitale) — nu e denumire MedLife izolată; altfel
    # _combina_linii_medlife lipește greșit următorul rând de analiză (ex. Progesteron după LH).
    if re.match(r"(?i)^\s*Interval\s*:", t):
        return False
    # Titluri «3. Biochimie serică» / «6. Hemoleucogramă» — nu le lipi de rândul următor (altfel absorb următoarea valoare).
    if re.match(
        r"^\s*\d+\.\s+(Biochimie|Bacteriologie|Electroforez|Examen|Hemoleucogram|Markeri|Antibiogram)",
        t,
        re.IGNORECASE,
    ):
        return False
    # Rânduri descriptive microbiologie / urocultură — nu le lipi de următorul rând ca „valoare”.
    if re.match(
        r"(?i)^(rezultat\s+cantitativ|organisme\s+absente|bacteriologie\s*[–-]\s*(urocultur|exudat))",
        t,
    ):
        return False
    low = t.lower()
    if low in ("test", "rezultat", "um", "interval de referinta", "interval de referință"):
        return False
    if _linie_este_exclusa(t) or _RE_NUME_PACIENT_ALL_CAPS.match(t):
        return False
    if _line_has_extractable_value_row(t):
        return False
    # Trebuie să conțină cel puțin un cuvânt lung (≥4 litere) SAU o abreviere majusculă (≥2 majuscule)
    # Exclude gunoi OCR de tipul "wen ee." sau "i i i" (3 litere trece vechiul prag dar nu e test medical)
    has_long_word = bool(re.search(r"[A-Za-zĂÂÎȘȚăâîșț]{4,}", t))
    has_abbreviation = bool(re.search(r"[A-ZĂÂÎȘȚ]{2,}", t))
    if not (has_long_word or has_abbreviation):
        return False
    # Linia conține un interval numeric (ex: "6.40 - 8.30") → e range de referință, nu test-only
    if re.search(r"\d+[.,]\d+\s*[-–]\s*\d+[.,]\d+", t):
        return False
    # Interval intreg fara zecimale (ex: "000-1400", "4-10") si fara alte valori zecimale → referinta
    if re.search(r"\b\d{2,}\s*[-–]\s*\d{2,}\s*$", t) and not re.search(r"\d[.,]\d", t):
        return False
    # Are deja model «nume valoare UM» pe același rând
    if re.search(r"(?<!\S)(?:[<>≤≥]\s*)?\d+[.,]\d+\s+[\w%µ*/]", t) or re.search(
        r"(?<!\S)(?:[<>≤≥]\s*)?\d+\s+(?:g/|mg|µ|fL|pg|U/|mIU|pmol|ng/|UI/)", t, re.I
    ):
        return False
    return True


def _combina_linii_medlife(lines: list[str]) -> list[str]:
    """
    Unește rânduri MedLife: denumire pe un rând, opțional «Ser, metoda…» pe următoarele,
    apoi rând cu «valoare UM interval» (uneori fără paranteze).
    """
    result: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        cur = lines[i]
        stripped = cur.strip()
        if not stripped:
            result.append(cur)
            i += 1
            continue
        if _line_has_extractable_value_row(stripped) or not _looks_like_medlife_test_only_line(
            stripped
        ):
            result.append(cur)
            i += 1
            continue
        j = i + 1
        while j < n and _RE_MEDLIFE_METHOD_LINE.match(lines[j].strip()):
            j += 1
        if j >= n:
            result.append(cur)
            i += 1
            continue
        tail = lines[j].strip()
        k_tail = j
        # OCR: «4.66» pe un rând, «*10^6/µL 3.9 - 5.3» pe următorul
        if tail and not _line_has_extractable_value_row(tail) and re.match(
            r"^\s*(?:[<>≤≥]\s*)?[\d.,]+\s*$", tail
        ):
            glued = tail
            kk = j
            found_row = False
            while kk + 1 < n and kk - j < 8:
                nxt = lines[kk + 1].strip()
                if not nxt or _RE_MEDLIFE_METHOD_LINE.match(nxt):
                    break
                if len(nxt) > 120:
                    break
                if not re.search(r"[\d%µ/<≥≤>ˣ\^a-zA-Z]", nxt, re.I):
                    break
                glued = glued + " " + nxt
                kk += 1
                if _line_has_extractable_value_row(glued):
                    tail = glued
                    k_tail = kk
                    found_row = True
                    break
            if not found_row:
                tail = lines[j].strip()
                k_tail = j
        if _line_has_extractable_value_row(tail):
            merged = f"{stripped} {tail}"
            result.append(merged)
            i = k_tail + 1
            continue
        # Valoare pe rând, interval pe următorul (OCR fragmentat)
        if j + 1 < n:
            t2 = lines[j + 1].strip()
            if RE_VALOARE_PARTIAL.match(tail) and re.search(
                r"[\d.,]+\s*[-–]\s*[\d.,]+", t2
            ):
                merged = f"{stripped} {tail} {t2}"
                result.append(merged)
                i = j + 2
                continue
        result.append(cur)
        i += 1
    return result


_RE_SANTE_VIE_VAL_LINIE = re.compile(
    r"^(?:[<>≤≥]\s*)?[\d.,]+\s+[a-zA-Z%µμg\^/\*][\w\^/\*\.]*",
)


def _linie_sante_vie_fara_valoare(s: str) -> bool:
    """Linia are denumire + interval dar valoarea lipseste (Sante Vie: 'Uree serica . 10-50 mg/dl -')."""
    if not re.search(r"\d", s):
        return False
    if _line_has_extractable_value_row(s):
        return False
    # Are un interval de forma N-M undeva
    if re.search(r"\b\d+[,.]?\d*\s*[-–]\s*\d+[,.]?\d*", s):
        # Nu are valoare numerica inainte de interval (valoarea ar fi prima cifra izolata)
        m_first_num = re.search(r"(?<![0-9,.])\b(\d+[,.]?\d*)\b", s)
        m_interval = re.search(r"\b(\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)", s)
        if m_first_num and m_interval and m_first_num.start() >= m_interval.start():
            return True
    return False


def _combina_linii_ocr_fragmente_valoare(lines: list[str]) -> list[str]:
    """
    După MedLife: unește linii care încep doar cu număr (OCR a tăiat valoarea de UM+interval).
    Dacă ultima linie emisă pare doar denumire analiză, lipește rândul de valoare de ea.
    Sante Vie: unește linia 'Denumire . interval' cu linia 'valoare UM interval' de pe linia urm.
    """
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        s = raw.strip()
        if not s:
            out.append(raw)
            i += 1
            continue
        # Sante Vie: linie cu denumire + interval fara valoare → lipeste linia urmatoare cu valoarea
        if _linie_sante_vie_fara_valoare(s) and i + 1 < n:
            nxt = lines[i + 1].strip()
            if nxt and _RE_SANTE_VIE_VAL_LINIE.match(nxt) and not _linie_este_exclusa(nxt):
                out.append(s + " " + nxt)
                i += 2
                continue
        if not _line_has_extractable_value_row(s) and re.match(
            r"^\s*(?:[<>≤≥]\s*)?[\d.,]+\s*$", s
        ):
            glued = s
            k = i
            found = False
            while k + 1 < n and k - i < 8:
                nxt = lines[k + 1].strip()
                if not nxt or _RE_MEDLIFE_METHOD_LINE.match(nxt):
                    break
                if len(nxt) > 120:
                    break
                if not re.search(r"[\d%µ/<≥≤>ˣ\^a-zA-Z]", nxt, re.I):
                    break
                glued = glued + " " + nxt
                k += 1
                if _line_has_extractable_value_row(glued):
                    found = True
                    break
            if found:
                if out and _looks_like_medlife_test_only_line(out[-1].strip()):
                    out[-1] = out[-1].strip() + " " + glued
                else:
                    out.append(glued)
                i = k + 1
                continue
        out.append(raw)
        i += 1
    return out


def _strip_dash_value_prefix(s: str) -> str:
    """
    Sterge liniuta/cratima initiala ca sa nu fie exclusa de _LINII_EXCLUSE (care exclude antet cu linie minus).
    - MedLife PDR: '- 76.2 fL' (valoare continuare coloana)
    - SCJUB scanat: '- eGFR*', '- Clearance la creatinina*' (sub-item marker sectiune)
    - SCJUB scanat OCR: '_- eGFR*' (underscore + linie, artefact OCR de chenar tabel)
    - SCJUB scanat OCR: '_Globuline alfa', '_UROBILINOGEN,' (underscore inainte de litera)
    """
    m = re.match(r"^_?[-–]\s+(\w)", s)
    if m:
        return s[m.start(1):]
    # Underscore izolat inainte de litera (artefact OCR SCJUB: _Globuline, _UROBILINOGEN)
    if re.match(r"^_[A-Za-zĂÂÎȘȚăâîșț]", s):
        return s[1:]
    return s


_RE_LEADING_TYPOGRAPHIC_QUOTES = re.compile(r'^[\u201e\u201c\u201d\u00ab\u00bb]+')


def _strip_leading_typographic_quotes(s: str) -> str:
    """Strip leading OCR typographic quotes (artefact of dot/bullet marks in SCJUB format)."""
    return _RE_LEADING_TYPOGRAPHIC_QUOTES.sub('', s).strip()


def _strip_checkmark_v_prefix(s: str) -> str:
    """OCR citeste √ (checkmark) ca litera V — scoate prefixul 'V ' din linii Gaman cu valoare.
    Ex: 'V Vitamina B12 – 456 pg/mL' → 'Vitamina B12 – 456 pg/mL'.
    Nu modifica linii fara valoare (ex: 'V Folat seric' standalone = antet MedLife PDR).
    """
    if not s or not re.match(r'^[vV]\s+\S', s):
        return s
    rest = re.sub(r'^[vV]\s+', '', s, count=1)
    if _RE_GAMAN_DASH_ANY_VALUE.search(rest):
        return rest
    return s


# Detecteaza linia urmatoare care e o valoare (numeric sau dash+numeric) — context pentru V-prefix
_RE_NEXT_LINE_IS_VALUE = re.compile(
    r"^(?:"
    r"[<>≤≥]\s*\d|"              # comparator + cifra
    r"\d+[.,]?\d*\s*\S|"         # cifra direct (valoare + unitate)
    + _RE_DASH_UCR + r"\s*\d"    # dash + cifra (Gaman two-line)
    r")",
    re.UNICODE,
)


def _strip_v_prefix_before_value_lines(lines: list) -> list:
    """Elimina prefixul 'V ' (checkmark OCR) cand linia URMATOARE e o valoare numerica.

    Rezolva formatul Gaman multi-linie din PDF-uri Regina Maria scanate:
      'V Vitamina B12'  +  '456 pg/mL'  +  'Interval: 200 – 900'
    → 'Vitamina B12'   +  '456 pg/mL'  +  'Interval: 200 – 900'

    Nu atinge linii 'V Param' fara valoare pe urmatoarea linie (antet MedLife PDR real).
    """
    _RE_V_HDR = re.compile(r"^[vV]\s+[A-Za-zĂÂÎȘȚăâîșț]{4,}", re.UNICODE)
    result = list(lines)
    for i in range(len(result) - 1):
        li = (result[i] or "").strip()
        if not _RE_V_HDR.match(li):
            continue
        ln = (result[i + 1] or "").strip()
        if _RE_NEXT_LINE_IS_VALUE.match(ln) or _RE_INTERVAL_LABEL_LINIE.match(ln):
            result[i] = re.sub(r"^[vV]\s+", "", li, count=1)
    return result


def _strip_trailing_date_recoltare(linie: str) -> str:
    """
    Elimină de la sfârșitul liniei data recoltării / generării (DD.MM.YYYY [HH:MM]),
    astfel încât parserele (Bioclinica oneline, RE_VALOARE_LINIE) să vadă intervalul corect.
    Ex: „Glucoză 92 mg/dL (74-106) 22.02.2024" → „Glucoză 92 mg/dL (74-106)".
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
                        if prev and not _linie_este_exclusa(prev) and not _RE_NUME_PACIENT_ALL_CAPS.match(prev.strip()):
                            if not RE_VALOARE_LINIE.match(prev) and not _RE_VAL_UM_SIMPLU.match(prev):
                                if len(_RE_STRIP_NON_ALPHA.sub("", prev)) >= 3:
                                    param_precedent = prev
                                    break
                    if param_precedent:
                        result.append(f"{param_precedent} %")
                    # Emite val procentuala combinata
                    result.append(f"{lines[i + 1]} ({mi2.group(1)} - {mi2.group(2)})")
                    i += 4
                    continue

        # Caz 1c: «Nume analiză – valoare UM» + «Interval: min – max» (Gaman / raport digital)
        # → o linie cu interval în paranteze pătrate (parsare _parse_oneline m_nm_br) sau (≤ x) Bioclinica
        if i + 1 < len(lines):
            li = (lines[i] or "").strip()
            ln = (lines[i + 1] or "").strip()
            m_g = _RE_GAMAN_PARAM_VAL_UM.match(li)
            m_il = _RE_INTERVAL_LABEL_LINIE.match(ln) if m_g else None
            m_1t = _RE_INTERVAL_LABEL_SINGULAR_TXT.match(ln) if m_g else None
            m_ge = _RE_INTERVAL_LABEL_GE_NUM.match(ln) if m_g else None
            if m_g and m_il:
                name = m_g.group(1).strip()
                cmp_v = m_g.group(2) or ""
                val = m_g.group(3)
                um = (m_g.group(4) or "").strip()
                val_disp = (cmp_v + val).strip()
                lo, hi = m_il.group(1), m_il.group(2)
                lo_f, hi_f = _parse_european_number(lo), _parse_european_number(hi)
                if (
                    len(name) >= 2
                    and lo_f is not None
                    and hi_f is not None
                    and lo_f < hi_f
                ):
                    if um:
                        result.append(f"{name} {val_disp} {um} [{lo} - {hi}]")
                    else:
                        result.append(f"{name} {val_disp} [{lo} - {hi}]")
                    i += 2
                    continue
            if m_g and m_1t:
                name = m_g.group(1).strip()
                cmp_v = m_g.group(2) or ""
                val = m_g.group(3)
                um = (m_g.group(4) or "").strip()
                val_disp = (cmp_v + val).strip()
                cmp_c = m_1t.group(1).strip()
                lim = m_1t.group(2).strip()
                if len(name) >= 2 and _parse_european_number(lim) is not None:
                    if um:
                        result.append(f"{name} {val_disp} {um} ({cmp_c} {lim})")
                    else:
                        result.append(f"{name} {val_disp} ({cmp_c} {lim})")
                    i += 2
                    continue
            if m_g and m_ge:
                name = m_g.group(1).strip()
                cmp_v = m_g.group(2) or ""
                val = m_g.group(3)
                um = (m_g.group(4) or "").strip()
                val_disp = (cmp_v + val).strip()
                thr = m_ge.group(1).strip()
                if len(name) >= 2 and _parse_european_number(thr) is not None:
                    if um:
                        result.append(f"{name} {val_disp} {um} (>= {thr})")
                    else:
                        result.append(f"{name} {val_disp} (>= {thr})")
                    i += 2
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


_RE_GENUS_MICRO_LINIE = re.compile(
    r"(?i)^(Staphylococcus|Streptococcus|Streptococ\b|Escherichia|Enterococcus|Candida|Klebsiella|"
    r"Pseudomonas|Enterobacteriaceae|Enterobacter\b|Proteus|Salmonella|Shigella|Neisseria|Acinetobacter|"
    r"Haemophilus|Bacteroides|Clostridium|Listeria|Mycobacterium|Legionella|Bacillus|"
    r"Aspergillus|Cryptococcus|Trichomonas|Giardia|Moraxella|Serratia|Eriaceae)\b",
)

# Regex precompilate pentru funcții apelate frecvent în loop (evită recompilare la fiecare linie)
_RE_STRIP_NON_LITERE = re.compile(r"[^a-zA-ZăâîșțĂÂÎȘȚ]")
_RE_LITERA_UNICA = re.compile(r"\b[a-zA-ZăâîșțĂÂÎȘȚ]\b")
_RE_STRIP_NON_ALPHA = re.compile(r"[^a-zA-Z]")
_RE_ZGOMOT_HEADER = re.compile(
    r"(?i)^(Denumire\s+Rezultat|Interval\s+de\s+referin[tț]a|Ser\s*/\s*Metoda|Ser\s*/\s*metoda|Ser\s*/\s*Test\s+calculat|"
    r"Test\s+Rezultat\s+Unitate|Subanaliz[aă]\s+Rezultat)"
)
_RE_STRIP_PREFIX_SIMBOLURI = re.compile(r"^[\s\u221A\u2713\u2714\u2610\u2611\u25AA\u2022\*\-\.]+")


def _organism_din_denumire_micro(denumire: str) -> Optional[str]:
    """Dacă denumirea arată ca organism (gen), o returnează pentru meta structurată."""
    d = (denumire or "").strip()
    if not d or len(d) > 120:
        return None
    return d if _RE_GENUS_MICRO_LINIE.match(d) else None


def _e_nou_rand_test_micro(s: str) -> bool:
    """
    Început de rând tipic în tabelul MedLife Microbiologie (titlu test),
    după care urmează rezultatul pe una sau mai multe linii.
    """
    s = (s or "").strip()
    if not s or len(s) > 200:
        return False
    if _RE_GENUS_MICRO_LINIE.match(s):
        return True
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
        r"(?i)^Toxina\s+[AB]\b",
        r"(?i)^Toxina\s+Clostridium",
        r"(?i)^Screening\s+MRSA\b",
        r"(?i)Toxina\s+Clostridium.*\bGDH\b",
        r"(?i)\btest\s+rapid\s+GDH\b",
    )
    return any(re.search(p, s) for p in patterns)


def _normalizeaza_rand_pipe(linie: str) -> str:
    """
    Normalizeaza linii cu separatoare pipe (format Spitalul Clinic Judetean Brasov si altele):
    'Creatinina serica | 0.97 | mg/dL | 0.50-0.90' -> 'Creatinina serica 0.97 mg/dL 0.50-0.90'
    Conditii: prima coloana = denumire (min 3 litere), a doua = numar.
    """
    # Strip leading pipe (OCR artifact from table border: '| Creatinina...')
    if linie.startswith("|"):
        linie = linie[1:].strip()
        if not linie:
            return ""
    # Strip trailing pipe(s)
    linie = re.sub(r'\s*\|+\s*$', '', linie)
    if "|" not in linie:
        return linie
    parts = [p.strip() for p in linie.split("|")]
    if len(parts) < 2 or len(parts) > 7:
        return linie
    if not parts[0] or not re.search(r"[^\W\d_]{3,}", parts[0]):
        return linie
    if not parts[1] or not re.search(r"^[<>≤≥]?\s*\d+[.,]?\d*\s*$", parts[1]):
        return linie
    return " ".join(p for p in parts if p)


def _expandeaza_rand_tab_diagnostic(linie: str) -> list[str]:
    """
    Transformă rânduri tabel (Test\\tRezultat\\tUnitate\\tInterval) în linii «Nume valoare UM (rest)»
    parsabile de _parse_oneline / Bioclinica. Antibiogramă 2 coloane → «Nume = Sensibil».
    """
    s = (linie or "").strip()
    if not s:
        return []
    if "\t" not in s:
        return [s]

    def _cel_antet_tabel(x: str) -> bool:
        xl = (x or "").strip().lower()
        return bool(
            re.fullmatch(
                r"(test|rezultat|unitate|interval(?: de referință| de referinta)?%?|"
                r"antibiotic|interpretare|subanaliza|subanaliză)",
                xl,
            )
        )

    parts = [p.strip() for p in s.split("\t")]
    parts = [p for p in parts if p != ""]
    if not parts:
        return []

    nhead = min(len(parts), 5)
    if nhead >= 2 and all(_cel_antet_tabel(p) for p in parts[:nhead]):
        return []

    p0 = parts[0]
    p1 = parts[1] if len(parts) > 1 else ""

    if len(parts) == 2 and p1.lower() in ("sensibil", "rezistent", "intermediar", "intermediu"):
        if not _cel_antet_tabel(p0):
            return [f"{p0} = {p1}"]

    if len(parts) >= 3:
        if _cel_antet_tabel(p0):
            return []
        name, val, um = parts[0], parts[1], parts[2]
        val = val.rstrip("*, ")
        rest = " ".join(parts[3:]).strip() if len(parts) > 3 else ""
        if rest:
            if not rest.startswith("("):
                rest = f"({rest})"
            return [f"{name} {val} {um} {rest}".strip()]
        return [f"{name} {val} {um}".strip()]

    return [re.sub(r"\s+", " ", s.replace("\t", " ")).strip()]


# TEO / Sf. Constantin: OCR uneori pune tot blocul «1.1.x … 1.2.y» pe un singur rând (fără \n între parametri).
_TRIPLE_CODE_SPLIT = re.compile(
    r"(?<=\S)\s+(?=\d+\.\d+\.\d+\s*\*?\s*[A-Za-zĂÂÎȘȚăâîșț(])",
)
_RAC_INLINE_SPLIT = re.compile(r"(?<=\S)\s+(?=\d\s*\*\s*RAC\b)", re.IGNORECASE)

# MedLife / TEO: OCR pune tot buletinul pe un singur rând (fără \n). Fără fragmentare,
# _este_linie_parametru refuză liniile >220 caractere → 0 analize.
_MEGA_FLAT_ROMAN = re.compile(
    r"(?<=[\.\)\w\u0103\u00e2\u00ee\u0219\u021b\u0102\u00c2\u00ce\u0218\u021a0-9%])\s+"
    r"(?=(?:II|III|IV|V|VI)\.\s)",
    re.IGNORECASE,
)
# «…Cefuroxime.II. Biochimie» — fără spațiu înainte de numerotare romană.
_MEGA_FLAT_ROMAN_DOT = re.compile(
    r"(?<=[a-zăâîșț0-9\u0103\u00e2\u00ee\u0219\u021b²³])\.(?=(?:II|III|IV|V|VI)\.\s)",
    re.IGNORECASE,
)
# «…(Risc … > 60).HDL» sau «…1,3).eGFR» — permite și eGFR la început după închidere.
_MEGA_FLAT_PAREN_DOT_PARAM = re.compile(
    r"\)(?:\.|\s)+\s*(?=(?:eGFR\b|[A-ZĂÂÎȘȚ][A-Za-zăâîșț0-9 ,()'/.%\-]{0,62}:\s*[\d<>+±≤≥]))",
    re.IGNORECASE,
)
# «…7,5)Densitate» sau «…66)Alfa1-globuline» — OCR fără punct după paranteză.
_MEGA_FLAT_PAREN_CAP = re.compile(
    r"\)(?=[A-ZĂÂÎȘȚ][A-Za-zăâîșț0-9\-]{3,}(?:\s|:))",
)
# «…13).V. Markeri» — punct între ) și numerotare romanică.
_MEGA_FLAT_PAREN_DOT_ROMAN = re.compile(r"(?<=\))\.\s*(?=(?:II|III|IV|V|VI)\.\s)", re.IGNORECASE)
# «…(Sânge/Ser) Trigliceride serice: 66» — paranteză + spațiu + parametru cu valoare.
_MEGA_FLAT_PAREN_SPACE_PARAM = re.compile(
    r"(?<=\))\s+(?=[A-ZĂÂÎȘȚ][a-zăâîșț0-9 ,()'/.%\-]{0,62}:\s*[\d<>+±≤≥])",
    re.IGNORECASE,
)
# «…completă:RBC (Eritrocite):» — două puncte înainte de abreviere caps + paranteză.
_MEGA_FLAT_COLON_ABBR_PAREN = re.compile(
    r":(?=[A-ZĂÂÎȘȚ]{2,10}\s*\()",
    re.IGNORECASE,
)
# «…serice:Albumină: 56» — lipire între subtitlu electroforeză și fracțiuni.
_MEGA_FLAT_COLON_CHAIN = re.compile(
    r"(?<=[a-zăâîșț0-9%²³\)]):\s*(?=[A-ZĂÂÎȘȚ][a-zăâîșț0-9]{1,24}\s*:)",
    re.IGNORECASE,
)
# «urină.Alte bacterii» sau «m².Potasiu» — punct după literă / cifră / ²³, urmat de majusculă (nu zecimal 100.000).
_MEGA_FLAT_LOWER_DOT_CAP = re.compile(
    r"(?<=[a-zăâîșț\u0103\u00e2\u00ee\u0219\u021b0-9%²³])\.(?=[A-ZĂÂÎȘȚ])",
)
# «…Peste limităLeucocite:» — lipire frecventă MedLife (fără punct între cuvinte).
_MEGA_FLAT_LIMITA_LEUCO = re.compile(r"(?i)(?<=limită)(?=Leucocite\s*:)", re.IGNORECASE)
# «…limităProteine» — același tip de lipire (sumar urină).
_MEGA_FLAT_LIMITA_PROTEINE = re.compile(r"(?i)(?<=limită)(?=Proteine)", re.IGNORECASE)


def _fragmenteaza_linii_mega_medlife_flat(lines: list[str]) -> list[str]:
    """
    Desparte buletine MedLife/TEO lipite pe un singur rând (fără coduri 1.1.1).
    Idempotentă pentru rânduri deja scurte.
    """
    lim = 220

    def _split_one_blob(s: str) -> list[str]:
        t = s.strip()
        if len(t) <= lim:
            return [t]
        prev = None
        for _ in range(14):
            if len(t) <= lim:
                break
            prev = t
            t = _MEGA_FLAT_ROMAN.sub("\n", t)
            t = _MEGA_FLAT_ROMAN_DOT.sub(".\n", t)
            t = _MEGA_FLAT_PAREN_SPACE_PARAM.sub("\n", t)
            t = _MEGA_FLAT_PAREN_DOT_PARAM.sub(")\n", t)
            t = _MEGA_FLAT_PAREN_CAP.sub(")\n", t)
            t = _MEGA_FLAT_PAREN_DOT_ROMAN.sub(")\n", t)
            t = _MEGA_FLAT_COLON_ABBR_PAREN.sub(":\n", t)
            t = _MEGA_FLAT_COLON_CHAIN.sub(":\n", t)
            t = _MEGA_FLAT_LIMITA_LEUCO.sub("\n", t)
            t = _MEGA_FLAT_LIMITA_PROTEINE.sub("\n", t)
            t = _MEGA_FLAT_LOWER_DOT_CAP.sub(".\n", t)
            if t == prev:
                break
        parts = [p.strip() for p in t.split("\n") if p.strip()]
        if len(parts) < 2:
            return [s.strip()]
        out: list[str] = []
        for p in parts:
            if len(p) > lim:
                out.extend(_split_one_blob(p))
            else:
                out.append(p)
        return out

    out_lines: list[str] = []
    for ln in lines:
        s = (ln or "").strip()
        if not s:
            continue
        out_lines.extend(_split_one_blob(s))
    return out_lines


def _fragmenteaza_linii_mega_teo(lines: list[str]) -> list[str]:
    """
    Desparte liniile foarte lungi cu multe coduri N.N.N (sumar urină etc.) în rânduri parsabile.
    """
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if len(s) < 120:
            out.append(ln)
            continue
        n_triple = len(_TRIPLE_CODE_SPLIT.findall(s))
        if n_triple < 2:
            out.append(ln)
            continue
        chunks = _TRIPLE_CODE_SPLIT.sub("\n", s).split("\n")
        merged: list[str] = []
        for ch in chunks:
            ch = ch.strip()
            if not ch:
                continue
            for sub in _RAC_INLINE_SPLIT.sub("\n", ch).split("\n"):
                t = sub.strip()
                if t:
                    merged.append(t)
        out.extend(merged if len(merged) >= 2 else [ln])
    return out


def _strip_trailing_interval_range(s: str) -> tuple[str, Optional[float], Optional[float]]:
    """
    Elimină de la sfârșit un interval «a - b» (inclusiv en-dash) ca să nu fie luat ultimul număr ca valoare.
    Ex.: «pH 5,0 5-7,5» → rest «pH 5,0», min=5, max=7.5
    """
    s_orig = s.rstrip()
    if len(s_orig) < 8:
        return s_orig, None, None
    m = re.search(r"\s+([\d.,]+)\s*[-–−]\s*([\d.,]+)\s*$", s_orig)
    if not m:
        return s_orig, None, None
    lo = _parse_european_number(m.group(1))
    hi = _parse_european_number(m.group(2))
    if lo is None or hi is None:
        try:
            lo = float(m.group(1).replace(",", "."))
            hi = float(m.group(2).replace(",", "."))
        except ValueError:
            return s_orig, None, None
    if lo > hi:
        lo, hi = hi, lo
    if hi > 1_000_000 or (hi - lo) > 100_000:
        return s_orig, None, None
    rest = s_orig[: m.start()].rstrip()
    if len(rest) < 3 or not re.search(r"[A-Za-zĂÂÎȘȚăâîșț]", rest):
        return s_orig, None, None
    return rest, float(lo), float(hi)


# Denumiri valide de analiză din 2–3 litere (altfel sunt eliminate ca artefact OCR în _add)
_DENUMIRI_ANALIZA_SCURTE = frozenset(
    {
        "ph",
        "tsh",
        "ft3",
        "ft4",
        "t3",
        "t4",
        "lh",
        "fsh",
        "vsh",
        "crp",
        "psa",
        "tgo",
        "tgp",
        "ldl",
        "hdl",
        "igg",
        "igm",
        "iga",
        # Capatan / Sysmex: indici morfologici pe 3 litere
        "vem",
        "hem",
        "chem",
        "mcv",
        "mch",
        "mpv",
        "rdw",
        "pdw",
        "pct",
    }
)


# Unirea/Regina Maria: două rânduri din tabelul sumar urină ajung lipite după _combina_linii_ocr_fragmente_valoare
# (ex. «Bilirubina … Negativ … Urobilinogen … Normal …»).
_RE_UNIREA_SUMAR_LIPIT = re.compile(
    r"(?i)(?<=\S)\s+(Urobilinogen|Glucoz[aă]\s+urinar[aă]|Nitrit[iş]|"
    r"Corpi\s+cetonici|Proteine\s+urinar[e]?)\b",
)


def _desface_rand_biochimie_urina_lipite(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        s = (ln or "").strip()
        if len(s) < 35:
            out.append(ln)
            continue
        parts: list[str] = [s]
        for _ in range(6):
            new_parts: list[str] = []
            changed = False
            for p in parts:
                m = _RE_UNIREA_SUMAR_LIPIT.search(p)
                if m is not None and m.start() > 12:
                    left = p[: m.start()].rstrip()
                    right = p[m.start() :].lstrip()
                    if len(left) >= 10 and len(right) >= 10:
                        new_parts.append(left)
                        new_parts.append(right)
                        changed = True
                        continue
                new_parts.append(p)
            parts = new_parts
            if not changed:
                break
        out.extend(parts)
    return out


def _normalize_unicode_hyphens_line(s: str) -> str:
    """Hyphen-uri Unicode înguste (ex. LDL‑colesterol) → ASCII, ca să prindă _RE_GAMAN / liniuțe."""
    if not s:
        return s
    t = s.replace("\ufeff", "")
    for ch in ("\u2011", "\u2010", "\u2012"):
        t = t.replace(ch, "-")
    return t


def _fragmenteaza_linii_ocr_fara_newlines(lines: list[str]) -> list[str]:
    """
    Dacă OCR întoarce puține linii foarte lungi (fără newline-uri), încearcă separare la tab / spații late.
    Recuperează structura de tabel când textul e lipit pe un singur rând.
    """
    if not lines:
        return lines
    if len(lines) > 12:
        return lines
    if sum(len(x) for x in lines) < 900:
        return lines
    out: list[str] = []
    for line in lines:
        if len(line) < 800:
            out.append(line)
            continue
        parts = re.split(r"(?:\t+| {3,})|\u00a0{2,}", line)
        if len(parts) >= 5:
            for p in parts:
                s = p.strip()
                if len(s) >= 8:
                    out.append(s)
        else:
            out.append(line)
    return out if out else lines


def extract_rezultate(text: str) -> list[RezultatParsat]:
    """
    Extrage analizele din text. Suporta:
    - Format Bioclinica (2 linii): parametru pe linia i, valoare+UM+interval pe linia i+1
    - Format Bioclinica (3 linii): parametru / valoare UM / (min - max) pe linii separate
    - Format MedLife/generic (1 linie): parametru + valoare + UM + interval pe aceeasi linie
    - Format tabel cu pipe (Spitalul Clinic Judetean Brasov etc.)
    Detecteaza automat sectiunile (Hemoleucograma, Biochimie etc.) si le ataseaza
    fiecarui rezultat impreuna cu ordinea din PDF.
    """
    lines_raw: list[str] = []
    for l in text.replace("\r", "\n").split("\n"):
        cleaned = corecteaza_ocr_linie_buletin(
            _strip_trailing_date_recoltare(
                _strip_leading_typographic_quotes(
                    _strip_dash_value_prefix(_normalizeaza_rand_pipe(l.strip()))
                )
            )
        )
        cleaned = _normalize_unicode_hyphens_line(cleaned)
        for piece in _expandeaza_rand_tab_diagnostic(cleaned):
            ps = piece.strip()
            if not ps:
                continue
            ps = _strip_leading_hash_marker_linie(_rewrite_observatii_mucus_capatan(ps))
            ps = _strip_checkmark_v_prefix(ps)
            if ps:
                lines_raw.append(ps)
    if len(lines_raw) <= 8 and sum(len(x) for x in lines_raw) > 1200:
        lines_raw = _fragmenteaza_linii_ocr_fara_newlines(lines_raw)
    # Regina Maria scanat: elimina prefixul 'V ' (√ citit de OCR) cand valoarea e pe linia urmatoare
    lines_raw = _strip_v_prefix_before_value_lines(lines_raw)
    # MedLife: unește denumire + rând(uri) metodă + valoare; apoi perechi Bioclinica
    lines = _lipire_valoare_rand_inainte_de_celule_epiteliale_capatan(
        _desface_rand_biochimie_urina_lipite(
            _fragmenteaza_linii_mega_medlife_flat(
                _fragmenteaza_linii_mega_teo(
                    _combina_linii_bioclinica(
                        _combina_linii_ocr_fragmente_valoare(_combina_linii_medlife(lines_raw))
                    )
                )
            )
        )
    )
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
        s = corecteaza_umar_numar_in_denumire((raw or "")[:80].lower().strip())
        s = re.sub(r"\s*:\s*$", "", s)
        return s

    def _pare_rand_tabel_concatenat(r: RezultatParsat) -> bool:
        """
        Elimină rezultate false unde denumirea și valoarea_text sunt de fapt două rânduri
        concatenate din tabel (ex: "Trombocite ...", valoare_text="Leucocite ...").
        """
        den = (r.denumire_raw or "").strip()
        vt = (r.valoare_text or "").strip()
        if r.valoare is not None or not den or not vt:
            return False
        den_has_numeric_unit = bool(re.search(r"\d+[.,]?\d*\s*(?:10\^\d|%|mg/dL|U/L|pg|ng|mm/h|/)", den, re.IGNORECASE))
        vt_has_numeric_unit = bool(re.search(r"\d+[.,]?\d*\s*(?:10\^\d|%|mg/dL|U/L|pg|ng|mm/h|/)", vt, re.IGNORECASE))
        vt_has_param = bool(re.search(r"\b(leucocite|hemoglob|hematocrit|trombocite|neutrofile|limfocite|monocite|eozinofile|bazofile|urobilinogen)\b", vt, re.IGNORECASE))
        return den_has_numeric_unit and vt_has_numeric_unit and vt_has_param

    def _este_zgomot_tabel_header(den: str) -> bool:
        d = (den or "").strip()
        if not d:
            return True
        if bool(_RE_ZGOMOT_HEADER.match(d)):
            return True
        dnorm = re.sub(r"\s+", " ", d.replace("\t", " "))
        if re.match(r"(?i)^test\s+rezultat\s+unitate\s+interval", dnorm[:120]):
            return True
        if re.match(r"(?i)^subanaliz[aă]\s+rezultat", dnorm[:120]):
            return True
        return False

    def _este_zgomot_microbiologie(r: RezultatParsat, categorie: Optional[str]) -> bool:
        if (categorie or "") != "Microbiologie":
            return False
        den = (r.denumire_raw or "").strip().lower()
        if den in {"microbiotei normale vaginale", "staphylococcus, streptococcus, genurile"}:
            return True
        if den.startswith("staphylococcus, streptococcus, genurile"):
            return True
        return False

    def _pare_mojibake_gunoi(den: str) -> bool:
        d = (den or "").strip()
        if not d:
            return True
        low = d.lower()
        if any(tok in d for tok in ("ÔÇ", "┬", "├", "�")):
            # Permitem trecerea doar daca linia are un nucleu clar de analiza.
            if not re.search(
                r"(bilirubin|tgo|ast|alt|rbc|wbc|hgb|hemoglob|hematocrit|"
                r"eozinofil|bazofil|creatinin|uree|glucoz|glicem|potasiu|sodiu|"
                r"toxina|mrsa|esbl|clostridium|enterobacter|moraxella)",
                low,
                re.IGNORECASE,
            ):
                return True
        return False

    def _add(r: Optional[RezultatParsat], categorie: Optional[str] = None) -> None:
        if r is None:
            return
        r.denumire_raw = _curata_denumire_rezultat(r.denumire_raw, r.valoare_text)
        if not r.denumire_raw or len(r.denumire_raw.strip()) < 2:
            return
        den_clean = (r.denumire_raw or "").strip()
        den_clean = re.sub(r"\s+", " ", den_clean.replace("\t", " ")).strip()
        if _RE_NUME_MEDIC.match(den_clean):
            return
        # Curata prefixe OCR frecvente: "1 * ", "i 8 * ", "a 3 ", etc.
        den_clean = re.sub(r"^(?:[a-z]\s+){1,3}(?=(?:\d|\*|[A-ZĂÂÎȘȚa-zăâîșț]))", "", den_clean, flags=re.IGNORECASE)
        den_clean = re.sub(r"^\d+\s*[\*\.\-]?\s*", "", den_clean)
        # Daca OCR a lipit rezultat/UM dupa separator de coloana, pastram doar denumirea.
        den_clean = re.sub(r"\s*\|.*$", "", den_clean).strip()
        den_clean = den_clean.strip(" -:;.,")
        # Strip calificatori text inclusi accidental in denumire din OCR multi-coloana
        # "PROTEINE TOTALE URINARE, negativ OO" → "PROTEINE TOTALE URINARE"
        den_clean = re.sub(
            r',\s*(?:negativ[ae]?|pozitiv[ae]?|absent[ae]?|prezent[ae]?)\b.*$',
            '', den_clean, flags=re.IGNORECASE
        ).strip()
        if not den_clean:
            return
        r.denumire_raw = den_clean
        den_low = den_clean.lower()
        den_norm = re.sub(r"[^a-z0-9]+", " ", den_low).strip()
        if den_low.startswith("metoda:"):
            return
        if any(
            kw in den_norm
            for kw in (
                "tiparit de",
                "cod document",
                "cod proba",
                "proba numarul",
                "punct ambulator",
                "punct recolta",
                "diagnostic",
                "medicina de laborator",
                "data inregistrarii",
                "valori in afara limitelor",
                "opiniile si interpretarile",
                "aceste rezultate pot fi folosite",
                "adresa jud",
                "act zv",
                "formular",
            )
        ):
            return
        if len(den_clean) < 3 and den_low not in _DENUMIRI_ANALIZA_SCURTE:
            return
        if re.fullmatch(r"[a-z]{2,3}", den_low) and den_low not in _DENUMIRI_ANALIZA_SCURTE:
            return
        if _pare_mojibake_gunoi(den_clean):
            return
        # Reutilizam filtrul central de "denumire gunoi" pentru a opri pseudo-analizele
        # administrative/artefact OCR care ajung in continuare dupa parse.
        if este_denumire_gunoi(den_clean):
            return
        if _este_zgomot_tabel_header(r.denumire_raw):
            return
        categorie = _categorie_inferata_din_denumire(r.denumire_raw, categorie)
        if _este_zgomot_microbiologie(r, categorie):
            return
        val_txt = (r.valoare_text or "").strip()
        if (categorie or "") != "Microbiologie":
            # In afara microbiologiei, ignoram pseudo-randurile fara rezultat real.
            if r.valoare is None and not val_txt:
                return
            if r.valoare is None and val_txt:
                vlow = val_txt.lower()
                if len(vlow) > 60 and not re.search(
                    r"(negativ|pozitiv|absent|prezent|normal|rar|frecvent|urme|reactiv)",
                    vlow,
                    re.IGNORECASE,
                ):
                    return
        if any(
            kw in den_norm
            for kw in (
                "foarte crescut",
                "nivel de risc",
                "valoare egfr",
                "infarct miocardic",
                "proteza valvulara",
            )
        ):
            return
        if _pare_rand_tabel_concatenat(r):
            return
        if _RE_DOAR_VALOARE_CA_PARAMETRU.match(r.denumire_raw.strip()):
            return
        # Valori extreme = eroare OCR (numar concatenat, cod pagina etc.) — nu analiza reala
        # Threshold 10M: sigur mai mare decat orice valoare reala (trombocite max ~1M/µL, eritrocite ~5M/µL)
        if r.valoare is not None and abs(r.valoare) > 10_000_000:
            return
        # Unitate suspicioasa: text lung concatenat OCR (ex "NumartombociteOOO262200OO")
        # Unitatile legitime au max ~15 caractere (ex "mL/min/1.73m2" = 13, "*10^6/µL" = 8)
        if r.unitate and len(r.unitate.strip()) > 20:
            return
        if r.valoare is not None:
            val_key: object = round(r.valoare, 3)
        else:
            val_key = (r.valoare_text or "").strip().lower()
        if getattr(r, "rezultat_tip", None) == "microbiology":
            # Dedupe mai agresiv pentru descrierile microbiologice multi-linie.
            val_key = re.sub(r"\s+", " ", str(val_key)).strip()
            val_key = re.sub(r"[^a-z0-9ăâîșț\s\-\.,:/]", "", val_key)[:180]
        # Include categoria în cheie: aceeași denumire (Leucocite, Hematii, Glucoză) poate apărea
        # în hemogramă și la sumar urină cu aceeași valoare text (ex. „negativ") — altfel pierdem rânduri.
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
        test_name_raw = linie.strip()
        j = idx + 1
        parts: list[str] = []
        head_val: Optional[str] = None
        m_head_colon = re.match(r"(?i)^(.+?):\s*(.+)$", test_name_raw)
        if m_head_colon:
            test_name = m_head_colon.group(1).strip()
            head_val = m_head_colon.group(2).strip()
        else:
            test_name = test_name_raw
        while j < len(lines):
            if line_sectiune[j] != "Microbiologie":
                break
            ln = lines[j].strip()
            if not ln:
                j += 1
                continue
            if _linie_este_exclusa(lines[j]):
                break
            if re.match(r"(?i)^Pagina\s+\d", ln):
                break
            if _e_nou_rand_test_micro(ln):
                break
            # Subtitlu MedLife între exudat și urocultură — nu face parte din cultura curentă
            if re.match(r"(?i)^bacteriologie\s*[–-]\s*urocultur", ln):
                break
            if re.match(r"(?i)^urocultur[aă]\s*$", ln):
                break
            if re.match(r"(?i)^examen\s+bacteriologic\s*,\s*micologic\s*$", ln):
                j += 1
                continue
            parts.append(ln)
            j += 1
        blob_lines: list[str] = []
        if head_val:
            blob_lines.append(head_val)
        blob_lines.extend(parts)
        if blob_lines:
            blob = "\n".join(blob_lines).strip()[:8000]
            den = _curata_denumire_rezultat(
                _strip_prefix_numar_linie(test_name),
                None,
            )
            if den and len(den) >= 2:
                org_micro = _organism_din_denumire_micro(den)
                _add(
                    RezultatParsat(
                        denumire_raw=den,
                        valoare=None,
                        valoare_text=blob,
                        unitate=None,
                        organism_raw=org_micro,
                        rezultat_tip="microbiology",
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

        # Tăiem interpretarea lipită de valoare («… (74-106) Normal», «… mg/dL > 60 Normal»)
        lv = _strip_suffix_interpretare_clasificare(linie_val.strip())
        m = RE_VALOARE_LINIE.match(lv)
        # Daca nu e format min-max, incearca format singular (≤ X) - ex: "2,260mg/dL (<= 0,33)"
        m_sing = None
        if not m:
            m_sing = RE_VALOARE_REF_SINGULAR.match(lv) or RE_BIOCLINICA_REF_SINGULAR.match(lv)
        m_dash = None
        if not m and not m_sing:
            m_dash = RE_VALOARE_LINIE_DASH.match(lv)
        m_part = None
        if not m and not m_sing and not m_dash:
            lv2 = re.sub(r"^[\s\•\-\*\.:;]+", "", lv).strip()
            m_part = RE_VALOARE_PARTIAL.match(lv2)
        m_slash = None
        if not m and not m_sing and not m_dash and not m_part:
            m_slash = RE_VALOARE_SLASH_UNIT.match(lv)
        if not m and not m_sing and not m_dash and not m_part and not m_slash:
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
        elif m_sing:
            # Format singular (≤ X): valoare si limita superioara
            valoare = _parse_european_number(m_sing.group(1))
            if valoare is None:
                continue
            unitate = m_sing.group(2).strip().replace(" ", "") or None
            interval_min = None
            interval_max = _parse_european_number(m_sing.group(3))
        elif m_dash:
            valoare = _parse_european_number(m_dash.group(1))
            if valoare is None:
                try:
                    valoare = float(m_dash.group(1).replace(",", "."))
                except ValueError:
                    continue
            unitate = m_dash.group(2).strip().replace(" ", "") or None
            interval_min = _parse_european_number(m_dash.group(3))
            interval_max = _parse_european_number(m_dash.group(4))
            if interval_min is None or interval_max is None:
                try:
                    interval_min = float(m_dash.group(3).replace(",", "."))
                    interval_max = float(m_dash.group(4).replace(",", "."))
                except ValueError:
                    interval_min = interval_max = None
            if interval_min is not None and interval_max is not None and interval_min >= interval_max:
                interval_min = interval_max = None
        elif m_slash:
            # Format «valoare/unitate» fără spațiu — ex: "4.650.000/mm3" (Bioclinica hemoleucograma)
            valoare = _parse_european_number(m_slash.group(1))
            if valoare is None:
                continue
            unitate = "/" + m_slash.group(2)
            interval_min = interval_max = None
        else:
            # Doar «valoare UM» pe linie (fără paranteze) — Bioclinica/Synevo pe 2 rânduri
            valoare = _parse_european_number(m_part.group(1))
            if valoare is None:
                try:
                    valoare = float(m_part.group(1).replace(",", "."))
                except ValueError:
                    continue
            unitate = (m_part.group(2) or "").strip().replace(" ", "") or None
            interval_min = interval_max = None
        denumire = ""
        cat_linie = line_sectiune[i]
        # Fereastra extinsa (30 linii) pentru a traversa headerele de pagina Bioclinica
        # care se intercaleaza intre parametru (pagina N) si valoare (pagina N+1)
        for j in range(i - 1, max(i - 30, -1), -1):
            cand = lines[j].strip()
            if not cand or _LINIE_NOTA.match(cand):
                continue
            # Sarim peste linii de header/footer de pagina (nu suntem "blocati")
            if _linie_este_exclusa(cand):
                continue
            # NU folosi ca parametru o linie care arata ca "Param Val UM (interval)" pe aceeasi linie
            # (format Bioclinica oneline) - altfel riscam: Trombocite pe linia 1, Leucocite pe 2,
            # valoare 267.000 pe 3 -> asociem gresit Leucocite cu 267.000
            if RE_BIOCLINICA_ONELINE.search(cand) or RE_BIOCLINICA_REF_SINGULAR.search(cand):
                break  # e un alt parametru complet - ne oprim
            # Nu folosi un rând deja complet (ex. Hematocrit 35.5 % …) ca „parametru" pentru valoarea de dedesubt
            if _parse_oneline(cand) is not None:
                continue
            if (_este_linie_parametru(cand)
                    and not RE_VALOARE_LINIE.match(cand)
                    and not RE_VALOARE_PARTIAL.match(cand)
                    and not RE_VALOARE_REF_SINGULAR.match(cand)):
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
        elif interval_min is not None and interval_max is None:
            if valoare < interval_min:
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


def _evalueaza_review_rezultat(r: RezultatParsat) -> list[str]:
    """
    Reguli conservative pentru semnalare semi-auto:
    nu blocăm salvarea, doar marcăm rezultatul pentru verificare.
    """
    reasons: list[str] = []
    den = (r.denumire_raw or "").strip()
    if not den:
        reasons.append("denumire_lipsa")
    if r.valoare is not None:
        if r.interval_min is not None and r.interval_max is not None:
            if r.interval_min >= r.interval_max:
                reasons.append("interval_invalid")
            elif (r.valoare < r.interval_min and r.flag == "H") or (r.valoare > r.interval_max and r.flag == "L"):
                reasons.append("flag_incongruent_interval")
        if abs(r.valoare) > 1_000_000:
            reasons.append("valoare_extrema")
    else:
        if not (r.valoare_text or "").strip():
            reasons.append("valoare_lipsa")
    if r.unitate and len(r.unitate.strip()) > 32:
        reasons.append("unitate_suspect_lunga")
    return reasons


def aplica_validari_review(rezultate: list[RezultatParsat]) -> list[RezultatParsat]:
    """Atașează markerul needs_review și motivele pentru audit post-upload."""
    for r in rezultate:
        reasons = _evalueaza_review_rezultat(r)
        r.review_reasons = reasons
        r.needs_review = bool(reasons)
    return rezultate


def audit_semnale_multi_buletin_laborator(text: str) -> dict:
    """
    Semnale pentru mai multe buletine / laboratoare în același text (fără `extract_rezultate`).

    Folosit la avertismente la salvare și în diagnostic; pentru sumar linii folosiți `audit_linii_text`.
    """
    return _audit_semnale_multi_buletin_laborator_impl(text)


def _audit_semnale_multi_buletin_laborator_impl(text: str) -> dict:
    """
    Semnale pentru PDF-uri cu mai multe buletine sau laboratoare amestecate.

    `resolve_laborator_id_for_text` se bazează pe începutul textului; aici scanăm tot documentul.
    """
    from backend.lab_detect import enumerate_lab_brand_mentions

    raw = text or ""
    cnps = enumerare_cnp_valide_ordine_aparitie(raw)
    labs = enumerate_lab_brand_mentions(raw)
    multi_cnp = len(cnps) > 1
    brand_names = {x.get("laborator") for x in labs if x.get("laborator")}
    multi_brand = len(brand_names) > 1
    repeat_brand = any(int(x.get("aparitii") or 0) >= 3 for x in labs)
    lung = len(raw) > 12000
    # Doar CNP-uri sau mărci diferite = compunere reală; multipagină același lab = repeat, nu „compus”
    compus = multi_cnp or multi_brand

    if multi_cnp and multi_brand:
        mesaj = (
            "Detectat: mai multe CNP-uri valide și mai multe rețele de laborator în text. "
            "Parsarea folosește primul CNP; catalogul ales automat poate fi din antet — verificați override laborator sau împărțiți PDF-ul."
        )
    elif multi_cnp:
        mesaj = (
            "Detectat: mai multe CNP-uri valide distincte. "
            "Se folosește primul CNP pentru pacient; rezultatele tuturor buletinelor pot fi amestecate — împărțiți PDF-ul sau importați separat."
        )
    elif multi_brand:
        mesaj = (
            "Detectat: mai multe mărci de laborator în același text. "
            "Normalizarea aliasurilor folosește un singur laborator (din antet/override) — pentru analize corecte, setați laboratorul potrivit sau separați buletinele."
        )
    elif repeat_brand and lung:
        mesaj = (
            "Aceeași marcă de laborator apare de multe ori (antet pe fiecare pagină sau buletine consecutive). "
            "Dacă lipsește analize, verificați OCR și secțiunile de la sfârșitul documentului."
        )
    elif cnps:
        mesaj = "Un singur CNP distinct detectat; fără semnal clar de compunere din mai multe rețele."
    else:
        mesaj = "Nu s-a găsit CNP valid în text (Verificare poate folosi CNP temporar)."

    return {
        "cnp_distincte": cnps[:12],
        "numar_cnp_distincte": len(cnps),
        "matchuri_cnp_valide_pozitii_unice": numara_matchuri_cnp_valide(raw),
        "laboratoare_mentionate_tot_textul": labs,
        "pdf_probabil_compus_multi_buletin": bool(compus),
        "mesaj_scurt": mesaj,
    }


def audit_linii_text(text: str) -> dict:
    """
    Sumar linii text vs filtre și vs rezultate extrase — diagnostic Verificare / admin.
    Folosește aceleași predicate ca parsarea; nu modifică starea.
    """
    raw = text or ""
    lines = [l.strip() for l in raw.replace("\r", "\n").split("\n") if l.strip()]
    total = len(lines)
    exclusa = sum(1 for l in lines if _linie_este_exclusa(l))
    candidat_param = sum(1 for l in lines if _este_linie_parametru(l))
    non_admin = [l for l in lines if not _linie_este_exclusa(l)]
    respinse_dupa_admin = sum(1 for l in non_admin if not _este_linie_parametru(l))
    gunoi_heuristic = sum(
        1 for l in non_admin if (not _este_linie_parametru(l)) and _este_gunoi_ocr(l)
    )
    try:
        rez = extract_rezultate(raw)
        n_ext = len(rez)
        err_ext = None
    except Exception as ex:
        n_ext = 0
        err_ext = str(ex)[:240]
    out: dict = {
        "total_linii_non_goale": total,
        "linii_excluse_administrativ": exclusa,
        "linii_acceptate_ca_parametru": candidat_param,
        "linii_dupa_admin_nu_sunt_parametru": respinse_dupa_admin,
        "linii_respinse_cu_estimare_gunoi_ocr": gunoi_heuristic,
        "rezultate_extractate": n_ext,
        "semnale_multi_buletin_laborator": _audit_semnale_multi_buletin_laborator_impl(raw),
    }
    if err_ext:
        out["extragere_eroare"] = err_ext
    return out


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
    nume, prenume = _sanitize_nume_prenume_final(nume, prenume)
    # Siguranță suplimentară: OCR uneori lasă «CNP:» în câmpul Prenume
    if prenume and _prenume_invalid(_curata_camp_prenume(prenume)):
        prenume = None
    rezultate = aplica_validari_review(extract_rezultate(text))
    return PatientParsed(cnp=cnp, nume=nume or "Necunoscut", prenume=prenume, rezultate=rezultate)
