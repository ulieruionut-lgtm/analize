import re
test = "NITU MATEI    M, 1 an"
print(repr(test))
print(f"Len: {len(test)}")
print(f"Last 5: {repr(test[-5:])}")

patterns = [
    r".*\s[MF]\s*,\s*\d+\s*(?:ani?|luni?)",
    r".*\s[MF]\s*,\s*\d+\s*an",
    r".*[MF],\s*\d+\s*an",
    r".+[MF],\s+\d+\s+an",
]
for p in patterns:
    m = re.match(p, test, re.IGNORECASE)
    print(f"Pattern {p!r}: {'MATCH' if m else 'NO MATCH'}")

# Incearca sa intelegi de ce nu matchuieste
# Maybe the spaces in MATEI   are tabs?
print("\nOrd chars la 10-18:", [ord(c) for c in test[10:18]])
