"""
Verificare structura completa a primei analize din raspuns
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

analize = resp.get("analize", [])
print(f"Total analize: {len(analize)}")
if analize:
    print("\n=== Prima analiza (toate cheile) ===")
    print(json.dumps(analize[0], indent=2, ensure_ascii=False))
    print("\n=== A 4-a analiza (Hemoglobina) ===")
    if len(analize) >= 4:
        print(json.dumps(analize[3], indent=2, ensure_ascii=False))
