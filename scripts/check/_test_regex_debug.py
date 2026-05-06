import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

test = "NITU MATEI    M, 1 an"
p1 = re.compile(r".*\s[MF]\s*,\s*\d+\s*(?:ani|luni)", re.IGNORECASE)
p2 = re.compile(r".*\s[MF]\s*,\s*\d+\s*(?:an|lun)", re.IGNORECASE)
p3 = re.compile(r"[MF]\s*,\s*\d+\s*(?:ani|luni)", re.IGNORECASE)

print(f"p1 match: {bool(p1.match(test))}")
print(f"p2 match: {bool(p2.match(test))}")  
print(f"p3 search: {bool(p3.search(test))}")

# Testare directa
import re
m = re.match(r".*\s[MF]\s*,\s*\d+\s*(?:ani|luni)", test, re.IGNORECASE)
print(f"direct match: {m}")

# Verifica ce matchuieste
for i, c in enumerate(test):
    print(f"  {i}: {repr(c)}")
