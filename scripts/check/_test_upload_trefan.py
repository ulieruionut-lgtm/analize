"""
Trimite PDF-ul la aplicatia live si arata rezultatul complet.
"""
import urllib.request
import urllib.parse
import json
import mimetypes

pdf_path = r"c:\Users\User\OneDrive\Desktop\buletine analize\Analize\Trefan Victor.pdf"
url = "https://web-production-2a2ad.up.railway.app/upload?traceback=1"

# Construieste multipart form
boundary = "----PyBoundary1234567890"
with open(pdf_path, "rb") as f:
    pdf_data = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="Trefan Victor.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + pdf_data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    url,
    data=body,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Cookie": "",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
        print(json.dumps(resp, indent=2, ensure_ascii=False)[:8000])
except urllib.error.HTTPError as e:
    body_err = e.read().decode(errors="replace")[:2000]
    print(f"HTTP {e.code}: {body_err}")
except Exception as e:
    print(f"Error: {e}")
