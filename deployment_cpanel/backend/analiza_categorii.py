"""
Mapare cod_standard → categorie de afișare (aliniată clinic: Hematologie, Biochimie,
Hormoni tiroidă, Urină, Microbiologie, …).

Folosit la tab „Analize necunoscute”: grupare în dropdown și filtrare după categoria din PDF.
"""
from __future__ import annotations

# Coduri tipice din seed / 004_pg (majuscule)
_HEMO = frozenset({
    "WBC", "RBC", "HB", "HCT", "MCV", "MCH", "MCHC", "RDW", "PLT", "MPV", "PDW", "PCT",
    "NEUTROFILE_PCT", "NEUTROFILE_NR", "LIMFOCITE_PCT", "LIMFOCITE_NR",
    "MONOCITE_PCT", "MONOCITE_NR", "EOZINOFILE_PCT", "EOZINOFILE_NR",
    "BAZOFILE_PCT", "BAZOFILE_NR", "VSH", "RETICULOCITE", "NRBC",
})
# TSH / FT3 / FT4 NU sunt biochimie — sunt hormoni tiroidieni (clasificare clinică)
_BIOCHIMIE = frozenset({
    "GLUCOZA_FASTING", "GLUCOZA", "CREATININA", "UREE", "ACID_URIIC", "BILIRUBINA_TOTALA",
    "BILIRUBINA_DIRECTA", "ALT", "AST", "GGT", "FOSFATAZA_ALCALINA", "COL_TOTAL",
    "HDL", "LDL", "TRIGLICERIDE", "COLESTEROL", "PROTEINE_TOTALE", "ALBUMINA",
    "CALCIU", "CALCIU_IONIC", "FOSFOR", "MAGNESIU", "SODIU", "POTASIU", "FERITINA",
    "FIER", "TIBC", "TRANSFERRINA", "CRP", "PROCALCITONINA", "LACTAT", "AMILAZA",
    "LIPAZA", "CK", "CK_MB", "LDH", "HOMOCISTEINA", "VIT_D", "VIT_B12", "FOLAT",
    "PSA", "PSA_LIBER", "CORTIZOL", "INSULINA", "PEPTID_C",
    "HBGLIC", "HBA1C", "FRUCTOZAMINA", "MICROALBUMINURIE", "RATIO_ACR",
    "EGFR", "RFG", "RFGE",
})
_TIROIDA = frozenset({"TSH", "FT3", "FT4", "ANTI_TPO", "ANTI_TG", "TRAB", "CALCITONINA"})
_URINA = frozenset({
    "UROBILINOGEN", "BILIRUBINA_U", "GLUCOZA_U", "CORPI_CETONICI", "DENSITATE_U",
    "PH_U", "PROTEINE_U", "SANG_U", "NITRITI_U", "LEUCOCITE_U", "HEMATII_U",
    "MICROALBUMINA_U", "ALBUMINA_U", "MUCUS_U", "CILINDRI_U", "CRISTALE_U",
})
_IMUNO = frozenset({
    "IGE", "IGG", "IGA", "IGM", "COMPLEMENT_C3", "COMPLEMENT_C4", "ANA", "RF",
    "ANTI_CCP", "HBSAG", "ANTI_HBS", "ANTI_HCV", "ANTI_HIV", "VDRL", "TPHA",
})
_HORMONI = frozenset({
    "FSH", "LH", "PROLACTINA", "ESTRADIOL", "PROGESTERONA", "TESTOSTERON",
    "BHCG", "PTH", "ACTH", "GH", "IGF1",
})
_COAG = frozenset({
    "INR", "TP", "APTT", "FIBRINOGEN", "D_DIMER", "ANTITROMBINA",
})
_MARKERI = frozenset({
    "CEA", "CA125", "CA19_9", "CA15_3", "AFP", "CYFRA", "NSE", "SCC",
})
_MINERALE = frozenset({
    "ZN", "CU", "SE", "CR",
})
# Coduri explicite microbiologie (dacă există în catalog)
_MICROBIO_CODURI = frozenset({
    "UROCULTURA", "ANTIBIOGRAMA", "HEMOCULTURA", "COPROCULTURA", "EXUDAT",
})

# Fragmente în cod_standard (majuscule) — evităm „CULTUR” generic (apare în cuvinte omonime)
_MICROBIO_KEYWORDS = (
    "CHLAMYD",
    "MYCOPLAS",
    "UREAPLAS",
    "TRACHOMATIS",
    "UROCULT",
    "CULTURA",
    "CULTURI",
    "CULTURĂ",
    "ANTIBIOGRAM",
    "HEMOCULTUR",
    "COPROCULTUR",
    "MICROBIO",
    "MICROSCOP",
    "CITOBACTERIOLOG",
    "CITOBACTER",
    "PARAZITO",
    "VIROLOG",
    "CANDIDA",
    "FUNGI",
    "FUNGIC",
    "LEVUR",
    "EXUDAT",
    "VAGINAL",
    "MICROBIOT",
    "SECRETIE_VAG",
    "SECRETIE_",
    "SECREȚIE",
    "EXAMEN_MICRO",
    "AG_CHLAM",
    "AG_HBS",
    "PCR_",
)


def _cod_microbiologie(c: str) -> bool:
    u = (c or "").strip().upper().replace(" ", "_")
    if u in _MICROBIO_CODURI:
        return True
    return any(k in u for k in _MICROBIO_KEYWORDS)


def _cod_urina_din_nume(c: str) -> bool:
    u = (c or "").strip().upper().replace(" ", "_")
    if u in _URINA:
        return True
    # Nu folosim „U” singur (litera apare în „MUCUS” fără legătură cu urină)
    if "MUCUS_U" in u or u.startswith("MUCUS_") or "MUCUS_URIN" in u:
        return True
    if "URIN" in u or u.endswith("_U") or "_U_" in u:
        return True
    return False


def categorie_grup_pentru_cod(cod: str) -> str:
    """
    Returnează eticheta de grup pentru analiza standard (pentru <optgroup> / filtre).
    Ordinea reflectă ierarhia clinică (tiroidă înainte de biochimie pentru FT4).
    """
    c = (cod or "").strip().upper().replace(" ", "_")
    if not c:
        return "Alte analize"
    if c in _HEMO:
        return "Hemoleucogramă / hematologie"
    if c in _TIROIDA or c.startswith("FT") or c.startswith("TSH") or "TIROID" in c:
        return "Hormoni tiroidieni"
    if c in _HORMONI:
        return "Hormoni (endocrinologie)"
    if _cod_microbiologie(c):
        return "Microbiologie / infecțioase"
    if c in _BIOCHIMIE:
        return "Biochimie / metabolism"
    if _cod_urina_din_nume(c):
        return "Examen urină"
    if c in _IMUNO:
        return "Imunologie / serologie"
    if c in _COAG:
        return "Coagulare / hemostază"
    if c in _MARKERI:
        return "Markeri tumorali"
    if c in _MINERALE:
        return "Minerale / oligoelemente"
    if "URIN" in c or c.endswith("_U"):
        return "Examen urină"
    return "Alte analize"


def potrivire_categorie_pdf_cu_grup(categorie_pdf: str | None, grup_cod: str) -> bool:
    """
    True dacă grupul analizei standard pare compatibil cu categoria extrasă din buletin.
    """
    if not categorie_pdf or not categorie_pdf.strip():
        return True
    p = categorie_pdf.strip().lower()
    g = grup_cod.lower()
    if "hemo" in p or "leuco" in p or "formula" in p or "hemat" in p:
        return "hemoleuco" in g or "hemat" in g
    if "urin" in p or "sediment" in p or "sumar" in p:
        return "urin" in g
    if "biochim" in p or "lipid" in p:
        return "biochim" in g or "metabol" in g
    if "microbio" in p or "cultur" in p or "infec" in p or "bacterio" in p or "parazit" in p:
        return "microbiol" in g or "infec" in g
    if "imun" in p or "serol" in p:
        return "imun" in g or "serol" in g
    if "hormon" in p or "tiroid" in p or "endocrin" in p:
        return "hormon" in g or "tiroid" in g
    if "coagul" in p or "hemost" in p:
        return "coagul" in g or "hemost" in g
    if "marker" in p or "tumor" in p or "onco" in p:
        return "marker" in g or "tumor" in g
    if "miner" in p or "electrol" in p:
        return "miner" in g or "oligoe" in g
    if "inflam" in p:
        return "biochim" in g or "hemat" in g
    if "electroforez" in p:
        return "alte" in g or "biochim" in g
    return True
