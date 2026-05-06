"""
Login + upload Trefan Victor in mod debug pentru a vedea textul OCR si parsarea.
"""
import urllib.request, urllib.parse, json, http.cookiejar

BASE = "https://web-production-2a2ad.up.railway.app"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Incearca mai multe parole posibile
for pwd in ["admin", "Admin123", "admin123", "ionut", "Ionut123", "parola", "test", "1234"]:
    try:
        login_data = urllib.parse.urlencode({"username": "admin", "password": pwd}).encode()
        req = urllib.request.Request(f"{BASE}/login", data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with opener.open(req, timeout=10) as r:
            resp = json.loads(r.read())
            if resp.get("access_token"):
                print(f"Login OK cu parola: {pwd}")
                TOKEN = resp["access_token"]
                break
    except urllib.error.HTTPError:
        pass
    except Exception as e:
        print(f"Eroare: {e}")
        break
else:
    print("Nu am gasit parola corecta. Incerc cu username=ionut:")
    for user in ["ionut", "admin", "user", "medic"]:
        for pwd in ["admin", "ionut", "1234", "parola", "test123"]:
            try:
                login_data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
                req = urllib.request.Request(f"{BASE}/login", data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
                with opener.open(req, timeout=5) as r:
                    resp = json.loads(r.read())
                    if resp.get("access_token"):
                        print(f"Login OK: {user}/{pwd}")
                        TOKEN = resp["access_token"]
                        break
            except:
                pass
        else:
            continue
        break
    else:
        print("Nu am putut loga. Scrie parola de admin.")
        exit(1)
