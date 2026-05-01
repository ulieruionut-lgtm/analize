"""
Fixture text în format Gaman (Param – valoare UM + Interval: min – max).
Verifică parserul după modificările pentru lipirea rândurilor și diacritice.
"""
from __future__ import annotations

import textwrap

import pytest

from backend.parser import extract_rezultate


def _gaman_fixture_text() -> str:
    """58 analize — aceleași denumiri/valori ca în buletinul Gaman Luca (listă de referință)."""
    pairs: list[tuple[str, str, str, str, str]] = [
        ("VSH (Westergreen)", "13", "mm/h", "2", "30"),
        ("Eritrocite (RBC)", "4.87", "mil/µL", "4", "5.2"),
        ("Hemoglobină (HGB)", "12.9", "g/dL", "11", "14"),
        ("Hematocrit (HCT)", "38.5", "%", "34", "40"),
        ("MCV", "79.1", "fL", "75", "87"),
        ("MCH", "26.5", "pg", "24", "30"),
        ("MCHC", "33.5", "g/dL", "31", "37"),
        ("RDW-CV", "13.2", "%", "11.6", "14.8"),
        ("Leucocite (WBC)", "10.24", "mii/µL", "5", "15"),
        ("Neutrofile %", "39.8", "%", "30", "65"),
        ("Eozinofile %", "4.3", "%", "0", "8"),
        ("Bazofile %", "0.6", "%", "0.1", "1.2"),
        ("Limfocite %", "47.9", "%", "40", "70"),
        ("Monocite %", "7.4", "%", "0", "12"),
        ("Neutrofile abs.", "4.08", "mii/µL", "1.5", "8"),
        ("Eozinofile abs.", "0.44", "mii/µL", "0.1", "1"),
        ("Bazofile abs.", "0.06", "mii/µL", "0.01", "0.07"),
        ("Limfocite abs.", "4.9", "mii/µL", "3", "5"),
        ("Monocite abs.", "0.76", "mii/µL", "0.2", "1"),
        ("Trombocite (PLT)", "357", "mii/µL", "200", "490"),
        ("MPV", "8.8", "fL", "7.4", "13"),
        ("PDW-SD", "8.8", "fL", "8", "16.5"),
        ("ALT (GPT)", "23.04", "U/L", "15", "35"),
        ("AST (GOT)", "39.45", "U/L", "32", "69"),
        ("Bilirubină totală", "0.87", "mg/dL", "0.3", "1.2"),
        ("Calciu seric", "10.84", "mg/dL", "9.5", "10.8"),
        ("Creatinină serică", "0.37", "mg/dL", "0.18", "0.49"),
        ("eGFR", "181.2", "ml/min/1.73 m²", "", ""),  # singular
        ("Albumină %", "69.9", "%", "60.3", "72.8"),
        ("Alfa-1 globulină %", "1.7", "%", "1", "2.6"),
        ("Alfa-2 globulină %", "9.6", "%", "7.2", "11.8"),
        ("Beta-1 globulină %", "5.8", "%", "5.6", "9.1"),
        ("Beta-2 globulină %", "2.3", "%", "2.2", "5.7"),
        ("Gamma globulină %", "10.7", "%", "6.2", "15.4"),
        ("Raport A/G", "2.32", "", "1.1", "2.23"),
        ("Fosfatază alcalină", "218.45", "U/L", "163", "427"),
        ("Glucoză serică", "78.17", "mg/dL", "60", "99"),
        ("Fier seric (sideremie)", "127.71", "µg/dL", "14", "150"),
        ("pH urinar", "5.5", "", "5", "7"),
        ("Densitate urinară", "1023", "", "1010", "1030"),
        ("Feritină", "28.9", "ng/mL", "22", "322"),
        ("Proteina C reactivă (CRP)", "0.07", "mg/dL", "", ""),  # singular
    ]
    lines: list[str] = [
        "LISTA COMPLETĂ A ANALIZELOR – GAMAN LUCA ANDREI",
        "🩸 1. HEMATOLOGIE – Hemoleucogramă completă",
        "🧪 2. BIOCHIMIE",
        "🧬 3. ELECTROFOREZA PROTEINELOR SERICE",
        "🧪 4. BIOCHIMIE – continuare",
        "🚼 5. EXAMEN COMPLET DE URINĂ – sumar",
        "🔬 6. EXAMEN URINAR – sediment",
        "🧬 7. IMUNOLOGIE",
    ]
    for name, val, um, lo, hi in pairs:
        if name == "eGFR":
            lines.append(f"{name} – {val} {um}")
            lines.append("Interval: ≥60")
        elif name == "Proteina C reactivă (CRP)":
            lines.append(f"{name} – {val} {um}")
            lines.append("Interval: <0.5")
        elif um:
            lines.append(f"{name} – {val} {um}")
            lines.append(f"Interval: {lo} – {hi}")
        else:
            lines.append(f"{name} – {val}")
            lines.append(f"Interval: {lo} – {hi}")
    # Sumar / sediment — valori text (fără rând Interval obligatoriu)
    text_lines = [
        "Bilirubină – Negativ",
        "Urobilinogen – Normal",
        "Glucoză urinară – Normal",
        "Corpi cetonici – Absenți",
        "Eritrocite – Absente",
        "Leucocite – Negativ",
        "Nitriți – Absenți",
        "Proteine urinare – Absente",
        "Culoare – Galben deschis",
        "Claritate – Clar",
        "Celule epiteliale plate – Foarte rare",
        "Leucocite sediment – Foarte rare",
        "Eritrocite sediment – Absente",
        "Flora bacteriană – Absentă",
        "Celule epiteliale rotunde – Absente",
        "Mucus – Absent",
    ]
    lines.extend(text_lines)
    return "\n".join(lines)


def test_gaman_fixture_extracts_58_analyses() -> None:
    text = _gaman_fixture_text()
    rs = extract_rezultate(text)
    assert len(rs) == 58, f"Așteptat 58 analize, obținut {len(rs)}: {[r.denumire_raw for r in rs]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
