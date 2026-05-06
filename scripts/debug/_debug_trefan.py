"""
Upload Trefan Victor debug - versiunea corecta cu structura reala de raspuns.
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

try:
    with opener.open(req2, timeout=180) as r:
        resp = json.loads(r.read())
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode(errors="replace")[:500])
    exit(1)

print(f"=== ANALIZE GASITE: {resp.get('numar_analize', 0)} ===")
for a in resp.get("analize", []):
    print(f"  {a.get('denumire_raw','?'):40s} = {str(a.get('valoare','?')):10s} {str(a.get('unitate','?')):15s}")

print(f"\n=== TEXT OCR COMPLET ({resp.get('lungime_text',0)} chars) ===")
print(resp.get("text_primele_3000", "")[:6000])

print(f"\n=== LINII RAW (primele 100 din {resp.get('numar_linii',0)}) ===")
for item in resp.get("linii_0_80", [])[:100]:
    if isinstance(item, (list, tuple)):
        print(f"  {item[0]:3d}: {repr(item[1])[:150]}")
    else:
        print(f"  {repr(item)[:150]}")

print(f"\n=== LINII EXCLUSE ===")
for item in resp.get("linii_excluse", [])[:60]:
    if isinstance(item, (list, tuple)):
        print(f"  {item[0]:3d}: {repr(item[1])[:150]}")
    elif isinstance(item, str):
        print(f"  {repr(item)[:150]}")
    else:
        print(f"  {item}")
