import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pattern = re.compile(
    r"^[A-ZĂÂÎȘȚ]+(?:\s+[A-ZĂÂÎȘȚ]+)*\s+[MF]\s*,\s*\d+\s*(?:ani|luni)",
    re.IGNORECASE
)

test_cases = [
    "NITU MATEI    M, 1 an",
    "VLADASEL ELENA F, 52 ani",
    "M, 1 an",
    "ANTECEDENT",       # nu trebuie sa matchuiasca
    "Hematii",          # nu trebuie sa matchuiasca
    "TGO (ASAT)",       # nu trebuie sa matchuiasca
]

for t in test_cases:
    m = pattern.match(t)
    print(f"  {'MATCH' if m else 'NO MATCH'}: {t!r}")
