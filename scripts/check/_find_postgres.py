import psycopg2

# Incearca sa gaseasca proxy-ul public pentru parola gBQklIixjIoDowIRovLWEKEVmlcMoSwN
# Probabil e in proiectul ionut-analize-medicale (al doilea proiect Railway)

# Incercam cu hostname-ul public din ionut-analize-medicale (shortline.proxy.rlwy.net:17411)
# dar cu parola noua
url = "postgresql://postgres:gBQklIixjIoDowIRovLWEKEVmlcMoSwN@shortline.proxy.rlwy.net:17411/railway"
print("Incerc shortline.proxy.rlwy.net:17411 cu parola noua...")
try:
    conn = psycopg2.connect(url, connect_timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT current_database(), COUNT(*) FROM pacienti")
    row = cur.fetchone()
    print(f"SUCCESS! DB: {row[0]}, Pacienti: {row[1]}")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='rezultate_analize' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    print("Coloane:", cols)
    conn.close()
except Exception as e:
    print(f"FAIL: {e}")
