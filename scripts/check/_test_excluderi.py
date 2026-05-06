# -*- coding: utf-8 -*-
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Copiaza _LINII_EXCLUSE din parser (manual)
_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"Reproducerea|Pentru|Nu se|Este|Valori|Opiniile|Analizele|Se utilizeaz|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|18\.02\.|29\.05\.|"
    r"brasov@|RENAR|seria|serie|Nr\.\s+\d|Buletin de analize|Data tipar|"
    r"HEMOLEUCOGRAMA|Hemoleucogramă|Formula\s+leucocitară|BIOCHIMIE|IMUNOLOGIE|"
    r"Raspuns\s+rapid|ANTECEDENT|DATA\s+NA|^TRIMIS\s+DE$|"
    r"^RECOLTAT$|^LUCRAT$|^GENERAT$|^CNP$|"
    r"^STR\s+|^medic\s+[A-Za-z]|^\d{5}\s+Laborator|"
    r"^[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r".*\s[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r"sânge\s+integral|Conform\s+studiilor|favorabil\s+la|tratament\.|"
    r"Evaluarea\s+răspunsului|CRP-ratio|Interpretare:|"
    r"Răspuns\s+rapid|Răspuns\s+lent|Răspuns\s+bifazic|Răspuns\s+absent)",
    re.IGNORECASE,
)

# Linii problematice din PDF Nitu
tests = [
    'Răspuns rapid ........ < 0,4 (ziua 4 de terapie)',
    'Evaluarea răspunsului la terapia cu antibiotice:',
    'CRP-ratio (raport) - concentrație zilnică CRP/concentrație CRP ziua 0',
    'Interpretare:',
    'tratament.',
    'Conform studiilor de specialitate',
    'favorabil la terapia cu antibiotice',
    'M, 1 an',
    'Hemoleucogramă',
    'Formula leucocitară',
    '(sânge integral EDTA, citometrie de flux)',
    'NITU MATEI    M, 1 an',
]
for t in tests:
    r = bool(_LINII_EXCLUSE.match(t))
    print(f"  {'EXCL' if r else 'OK  '}: {repr(t)}")
