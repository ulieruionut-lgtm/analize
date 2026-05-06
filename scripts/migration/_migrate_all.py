"""
Ruleaza migrarile lipsa pe baza de date a aplicatiei live.
Apeleaza /api/migrate de mai multe ori pana toate migrările sunt aplicate.
"""
import urllib.request
import json
import time

base = "https://web-production-2a2ad.up.railway.app"

for attempt in range(5):
    print(f"\n--- Tentativa {attempt + 1} ---")
    try:
        req = urllib.request.Request(f"{base}/api/migrate", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            print("Migrate POST response:", json.dumps(data, indent=2, ensure_ascii=False))
            done = data.get("done", [])
            if "014_pg_rezultat_meta.sql" in str(done):
                print("\n✓ Migrarea 014 a fost aplicata!")
                break
            if not done:
                print("Nu mai sunt migratii de aplicat sau s-a terminat.")
                break
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:1000]
        print(f"HTTP {e.code}:", body)
        break
    except Exception as e:
        print("Eroare:", e)
        break
    time.sleep(2)

# Verifica final prin GET
print("\n--- Verificare finala GET /api/migrate ---")
try:
    with urllib.request.urlopen(f"{base}/api/migrate", timeout=30) as r:
        data = json.loads(r.read())
        print("GET response:", json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
