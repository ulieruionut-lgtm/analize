# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import urllib.request, urllib.error, urllib.parse

BASE_URL = "https://web-production-2a2ad.up.railway.app"

# Login
login_data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE_URL}/login", data=login_data, 
                              headers={"Content-Type": "application/x-www-form-urlencoded"})
try:
    resp = urllib.request.urlopen(req, timeout=15)
    token_data = json.loads(resp.read())
    token = token_data.get("access_token")
    print(f"Login OK, token: {token[:20]}...")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Login FAILED {e.code}: {body[:200]}")
    sys.exit(1)

auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Cauta pacientul Nitu
req = urllib.request.Request(f"{BASE_URL}/pacienti", headers=auth_headers)
resp = urllib.request.urlopen(req, timeout=15)
pacienti = json.loads(resp.read())
print(f"\nTotal pacienti: {len(pacienti)}")

nitu = [p for p in pacienti if 'nitu' in (p.get('nume', '') + p.get('prenume', '')).lower() or p.get('cnp') == '5240222080031']
print(f"Pacienti Nitu: {nitu}")

for p in nitu:
    pac_id = p['id']
    req = urllib.request.Request(f"{BASE_URL}/pacienti/{pac_id}/buletine", headers=auth_headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        buletine = json.loads(resp.read())
        print(f"\nBuletine pentru {p['nume']} {p['prenume']}: {len(buletine)}")
        for b in buletine:
            print(f"  [{b.get('id')}] {b.get('data_recoltare')} - {len(b.get('rezultate', []))} rezultate")
            for r in b.get('rezultate', []):
                print(f"    {r.get('denumire_standard', r.get('denumire_raw', '?'))} = {r.get('valoare')} {r.get('unitate', '')}")
    except Exception as ex:
        print(f"  Eroare: {ex}")
