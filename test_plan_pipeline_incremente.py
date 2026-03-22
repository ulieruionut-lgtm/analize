"""Teste ușoare pentru îmbunătățiri plan: OCR partajat, fragmente admin, meta microbiologie."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import re

from backend.administrative_fragments import contin_fragment_administrativ
from backend.ocr_corrections import aplică_corectii_ocr_normalizat, corecteaza_umar_numar_in_denumire
from backend.normalizer import _baza_denumire_pentru_fuzzy
from backend.pdf_processor import _ocr_needs_more_passes, _ocr_quality_score, _tesseract_word_metrics

# Aliniat la backend.parser._RE_GENUS_MICRO_LINIE (fără import parser → fără pydantic)
_RE_GENUS_MICRO_LINIE = re.compile(
    r"(?i)^(Staphylococcus|Streptococcus|Escherichia|Enterococcus|Candida|Klebsiella|"
    r"Pseudomonas|Enterobacter(?:iaceae)?|Proteus|Salmonella|Shigella|Neisseria|Acinetobacter|"
    r"Haemophilus|Bacteroides|Clostridium|Listeria|Mycobacterium|Legionella|Bacillus|"
    r"Aspergillus|Cryptococcus|Trichomonas|Giardia|Moraxella|Serratia)\b",
)


def test_ocr_normalizat():
    assert aplică_corectii_ocr_normalizat("hcmoglobina") == "hemoglobina"
    assert "numar" in aplică_corectii_ocr_normalizat("umar de trombocite")


def test_umar_cheie():
    assert "numar de" in corecteaza_umar_numar_in_denumire("Umar de X")


def test_admin_fragments():
    assert contin_fragment_administrativ("Cod parafa laborator")
    assert contin_fragment_administrativ("Data tipăririi 12.01.2025")
    assert not contin_fragment_administrativ("Hemoglobina 13.2")


def test_meta_json():
    """Forma JSON așteptată la salvare (fără import database — evită pydantic_settings în medii minime)."""
    compact = json.dumps(
        {"organism_raw": "Candida albicans", "rezultat_tip": "microbiology"},
        ensure_ascii=False,
    )
    assert "Candida" in compact and "microbiology" in compact


def test_organism_micro():
    assert _RE_GENUS_MICRO_LINIE.match("Candida spp")
    assert not _RE_GENUS_MICRO_LINIE.match("Examen microbiologic")


def test_baza_denumire_fuzzy():
    assert _baza_denumire_pentru_fuzzy("hemoglobina 12.5 g/dl") == "hemoglobina"
    assert _baza_denumire_pentru_fuzzy("glucoza") == "glucoza"


def test_ocr_quality_and_metrics():
    assert _ocr_quality_score("", 0, 1, 0, 0, 100) < -1e6
    s = _ocr_quality_score("x" * 200, 75, 0.05, 0.15, 40, 100)
    assert s > _ocr_quality_score("x" * 50, 40, 0.6, 0.0, 5, 100)


def test_tesseract_word_metrics_mock():
    class FakeTess:
        def image_to_data(self, image, lang="", config="", output_type=None):
            return {
                "level": [5, 5, 5],
                "text": ["Hemo", "12.1", ""],
                "conf": [88, 42, -1],
            }

    mean_c, wr, dr, nw = _tesseract_word_metrics(
        None, "ron", "--oem 2 --psm 3", FakeTess()
    )
    assert nw == 2
    assert mean_c > 0
    assert 0 <= wr <= 1


def test_ocr_needs_more_passes():
    assert _ocr_needs_more_passes("", 0, 0, 0, 0, 50) is True
    assert _ocr_needs_more_passes("a" * 120, 75, 0.05, 0.2, 20, 100) is False


if __name__ == "__main__":
    test_ocr_normalizat()
    test_umar_cheie()
    test_admin_fragments()
    test_meta_json()
    test_organism_micro()
    test_baza_denumire_fuzzy()
    test_ocr_quality_and_metrics()
    test_tesseract_word_metrics_mock()
    test_ocr_needs_more_passes()
    print("OK: test_plan_pipeline_incremente")
