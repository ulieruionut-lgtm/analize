import urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context()
base = "https://ionut-analize-app-production.up.railway.app"

data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(base + "/login", data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read())["access_token"]

req2 = urllib.request.Request(base + "/")
req2.add_header("Authorization", "Bearer " + token)
req2.add_header("Cookie", "access_token=" + token)
with urllib.request.urlopen(req2, context=ctx) as r:
    html = r.read().decode("utf-8")

checks = [
    "new-analiza-search",
    "filtreazaAnalizeSearch",
    "selecteazaAnaliza",
    "new-analiza-dropdown",
    "Hemoglobina, TSH",
    "adaugaRezultatNou",
]
print("=== Verificare cod deployed ===")
for c in checks:
    status = "OK   " if c in html else "LIPSA"
    print(f"  [{status}]: {c}")

# Arata si ultimul commit din pagina daca exista
import re
m = re.search(r"version[:\s]+([0-9a-f]{7,})", html, re.IGNORECASE)
if m:
    print(f"\n  Versiune detectata: {m.group(1)}")
else:
    print(f"\n  Lungime HTML: {len(html)} caractere")
