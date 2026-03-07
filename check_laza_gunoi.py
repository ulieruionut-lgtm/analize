import urllib.request, urllib.parse, json, ssl

ctx = ssl.create_default_context()
base = "https://ionut-analize-app-production.up.railway.app"

data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(base + "/login", data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read())["access_token"]

print("LOGIN OK")

# Pacient Laza - toate datele
req2 = urllib.request.Request(base + "/pacient/2780416131279")
req2.add_header("Authorization", f"Bearer {token}")
with urllib.request.urlopen(req2, context=ctx) as r:
    pacient = json.loads(r.read())

buletine = pacient.get("buletine", [])
print(f"Laza are {len(buletine)} buletine:")
for b in buletine:
    bid = b["id"]
    data_r = b.get("data_buletin") or b.get("data_recoltare", "?")
    rez = b.get("rezultate", [])
    print(f"\n=== Buletin ID={bid} data={data_r} ({len(rez)} analize) ===")
    for item in rez:
        std = item.get("analiza_standard_id")
        raw = item.get("denumire_raw", "?")
        val = item.get("valoare")
        rid = item.get("id")
        print(f"  rid={rid} | std={std} | [{raw}] = {val}")
