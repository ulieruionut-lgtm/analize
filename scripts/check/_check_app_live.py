"""
Verificare directa a bazei de date reale folosita de aplicatia web-production-2a2ad.up.railway.app
"""
import urllib.request
import json

# Interogheza /health pentru a vedea ce DB type foloseste
try:
    with urllib.request.urlopen("https://web-production-2a2ad.up.railway.app/health", timeout=10) as r:
        data = json.loads(r.read())
        print("Health response:", data)
except Exception as e:
    print("Health error:", e)

# Interogheza /api/pacienti pentru a vedea datele reale
try:
    req = urllib.request.Request(
        "https://web-production-2a2ad.up.railway.app/api/pacienti",
        headers={"Cookie": ""}  # fara auth, va da 401
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print("Pacienti:", data)
except urllib.error.HTTPError as e:
    print(f"Pacienti HTTP {e.code}:", e.reason)
except Exception as e:
    print("Pacienti error:", e)
