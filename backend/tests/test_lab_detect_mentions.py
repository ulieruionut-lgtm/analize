"""Mențiuni laborator în tot textul (PDF compus / mai multe rețele)."""

from backend.lab_detect import enumerate_lab_brand_mentions


def test_enumerate_lab_brand_mentions_two_brands() -> None:
    t = "Raport MedLife\n" + "x\n" * 30 + "Rezultate Bioclinica\nHemoglobină 14 g/dl"
    labs = enumerate_lab_brand_mentions(t)
    names = {x["laborator"] for x in labs}
    assert "MedLife" in names
    assert "Bioclinica" in names
    assert all("aparitii" in x and x["aparitii"] >= 1 for x in labs)


def test_enumerate_lab_brand_mentions_empty() -> None:
    assert enumerate_lab_brand_mentions("") == []
    assert enumerate_lab_brand_mentions("   ") == []
