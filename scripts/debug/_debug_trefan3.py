"""
Captura eroare 500 de la upload.
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
        print(f"OK! Analize: {resp.get('numar_analize', 0)}")
        for a in resp.get("analize", []):
            print(f"  {a.get('denumire_raw','?'):45s} = {str(a.get('valoare','?')):10s} {str(a.get('unitate','?')):15s}")
except urllib.error.HTTPError as e:
    body_err = e.read().decode(errors="replace")
    print(f"HTTP {e.code}:")
    print(body_err[:2000])
