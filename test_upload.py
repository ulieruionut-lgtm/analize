"""
Test upload PDF la serverul local. Rulează după ce ai pornit: uvicorn backend.main:app --reload

Utilizare:
  python test_upload.py              (PDF Bioclinica text)
  python test_upload.py scan         (PDF scanat)
  python test_upload.py "c:\calea\la\fisier.pdf"
"""
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instalează requests: pip install requests")
    sys.exit(1)

# PDF-uri predefinite din workspace
PDF_BIOCLINICA = Path(
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\9d724bf6-0e36-4501-99d0-020f9cde8bc0\analize bioclinica.pdf"
)
PDF_SCANAT = Path(
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1a3dd593-a973-4c73-a8ba-925351f31b52\Scan2025-12-19_100509.pdf"
)
BASE = "http://localhost:8000"


def main():
    if len(sys.argv) >= 2:
        arg = sys.argv[1].strip().lower()
        if arg == "scan":
            pdf_path = PDF_SCANAT
        else:
            pdf_path = Path(sys.argv[1])
    else:
        pdf_path = PDF_BIOCLINICA
    if not pdf_path.exists():
        print(f"Fișier negăsit: {pdf_path}")
        sys.exit(2)
    print(f"Trimit: {pdf_path.name} la {BASE}/upload ...")
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE}/upload",
            files={"file": (pdf_path.name, f, "application/pdf")},
            timeout=60,
        )
    print("Status:", r.status_code)
    try:
        j = r.json()
        if r.ok:
            print("OK:", j.get("message", ""))
            print("Pacient:", j.get("pacient"))
            print("Număr analize salvate:", j.get("numar_analize"))
            cnp = j.get("pacient", {}).get("cnp")
            if cnp:
                print(f"\nVezi pacienti: GET {BASE}/pacient/{cnp}")
        else:
            print("Eroare:", j.get("detail", r.text))
    except Exception:
        print(r.text)


if __name__ == "__main__":
    main()
