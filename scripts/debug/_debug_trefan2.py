"""
Afiseaza toate liniile RAW si cele excluse din raspunsul debug.
"""
import urllib.request, urllib.parse, json, http.cookiejar

BASE = "https://web-production-2a2ad.up.railway.app"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

login_data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE}/login", data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"})
with opener.open(req, timeout=10) as r:
    token = json.loads(r.read())["access_token"]

pdf_path = r"c:\Users\User\OneDrive\Desktop\buletine analize\Analize\Trefan Victor.pdf"
boundary = "----PyBoundary1234567890"
with open(pdf_path, "rb") as f:
    pdf_data = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="Trefan Victor.pdf"\r\n'
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

with opener.open(req2, timeout=180) as r:
    resp = json.loads(r.read())

linii = resp.get("linii_0_80", [])
print(f"=== TOATE LINIILE RAW ({resp.get('numar_linii',0)}) ===")
for item in linii:
    if isinstance(item, (list, tuple)):
        print(f"  {item[0]:3}: {repr(item[1])[:200]}")
    else:
        print(f"  {repr(item)[:200]}")

excluse = set()
for item in resp.get("linii_excluse", []):
    if isinstance(item, (list, tuple)):
        excluse.add(item[0])
    elif isinstance(item, str) and item.startswith("'") and ":" in item[:5]:
        pass

print(f"\n=== ANALIZE PARSATE ({resp.get('numar_analize', 0)}) ===")
for a in resp.get("analize", []):
    print(f"  {a.get('denumire_raw','?'):45s} = {str(a.get('valoare','?')):10s} {str(a.get('unitate','?')):15s} [{a.get('interval_min')}-{a.get('interval_max')}]")
