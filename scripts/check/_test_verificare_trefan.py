"""
Login + verificare PDF (debug mode) - arata ce analize gaseste si textul OCR.
"""
import urllib.request, urllib.parse, json, http.cookiejar

BASE = "https://web-production-2a2ad.up.railway.app"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Login
login_data = urllib.parse.urlencode({"username": "admin", "password": "admin"}).encode()
token = ""
try:
    req = urllib.request.Request(f"{BASE}/login", data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with opener.open(req, timeout=15) as r:
        resp = json.loads(r.read())
        token = resp.get("access_token", "")
        print("Login OK, token:", token[:30], "...")
except Exception as e:
    print("Login error:", e)

if not token:
    print("Nu am token, opresc.")
    exit(1)

# Upload cu debug=1
pdf_path = r"c:\Users\User\OneDrive\Desktop\buletine analize\Analize\Trefan Victor.pdf"
boundary = "----PyBoundary1234567890"
with open(pdf_path, "rb") as f:
    pdf_data = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="Trefan Victor.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + pdf_data + f"\r\n--{boundary}--\r\n".encode()

req2 = urllib.request.Request(
    f"{BASE}/upload?debug=1",
    data=body,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    },
    method="POST",
)

try:
    with opener.open(req2, timeout=120) as r:
        resp2 = json.loads(r.read())
        for fisier in resp2.get("fisiere", [resp2]):
            print(f"\n{'='*60}")
            print(f"Fisier: {fisier.get('nume', 'N/A')}")
            rez = fisier.get("rezultate", [])
            print(f"Analize gasite: {len(rez)}")
            for r in rez:
                print(f"  {r.get('denumire_raw')} = {r.get('valoare')} {r.get('unitate')} [{r.get('interval_min')}-{r.get('interval_max')}]")
            
            print(f"\n--- TEXT OCR (primele 4000 chars) ---")
            print(fisier.get("text_extras", fisier.get("text", ""))[:4000])
            
            print(f"\n--- LINII RAW (primele 80) ---")
            linii = fisier.get("linii_raw", fisier.get("linii", []))
            for i, l in enumerate(linii[:80]):
                print(f"  {i:3d}: {repr(l)[:120]}")
            
            print(f"\n--- LINII EXCLUSE (primele 30) ---")
            excluse = fisier.get("linii_excluse", [])
            for idx, l in excluse[:30]:
                print(f"  {idx:3d}: {repr(l)[:120]}")

except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode(errors="replace")[:1000])
except Exception as e:
    import traceback
    traceback.print_exc()
