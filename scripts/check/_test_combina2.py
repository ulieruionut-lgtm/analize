import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_RE_VAL_UM_SIMPLU = re.compile(
    r"^([\d.,]+)\s+([a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(
    r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)[^\d\n]*$"
)

test_pairs = [
    ('2.260 /mm³', '(1.500 - 8.700)/mm³'),
    ('56,78 %', '(22,00 - 63,00)%'),
    ('1.150 /mm³', '(3.000 - 10.000)/mm³'),
    ('28,89 %', '(32,00 - 63,00)%'),
    ('460 /mm³', '(150 - 1.200)/mm³'),
    ('74 U/L', '(9 - 80)'),
    ('13,3 g/dL', '(10,2 - 13,4)'),
]

for val, interval in test_pairs:
    m_val = _RE_VAL_UM_SIMPLU.match(val)
    m_int = _RE_INTERVAL_PARANTEZE.match(interval)
    ok = '✓' if m_val and m_int else '✗'
    print(f"  {ok} {repr(val)} + {repr(interval)}")
    if m_val and m_int:
        print(f"     → {val} ({m_int.group(1)} - {m_int.group(2)})")
    else:
        print(f"     val={bool(m_val)}, int={bool(m_int)}")
