"""
Verifica schema bazei de date folosite de aplicatia live.
"""
import urllib.request
import json

# Apeleaza /api/migrate cu GET pentru a rula migrarile
# (daca exista acel endpoint)
base = "https://web-production-2a2ad.up.railway.app"

try:
    with urllib.request.urlopen(f"{base}/api/migrate", timeout=30) as r:
        data = json.loads(r.read())
        print("Migrate response:", data)
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"Migrate HTTP {e.code}:", body)
except Exception as e:
    print("Migrate error:", e)
