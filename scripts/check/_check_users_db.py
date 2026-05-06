import psycopg2
conn = psycopg2.connect("postgresql://postgres:gBQklIixjIoDowIRovLWEKEVmlcMoSwN@maglev.proxy.rlwy.net:48480/railway",
                        connect_timeout=10)
cur = conn.cursor()

# Verifica daca conexiunea merge
try:
    cur.execute("SELECT current_database()")
    print("DB:", cur.fetchone())
except Exception as e:
    print("Nu pot conecta cu aceasta parola:", e)
    conn.close()
    exit()

# Cauta utilizatorii
try:
    cur.execute("SELECT username, password_hash FROM utilizatori LIMIT 5")
    rows = cur.fetchall()
    print("Utilizatori:", rows)
except Exception as e:
    print("Tabel utilizatori eroare:", e)

try:
    cur.execute("SELECT username, password_hash FROM users LIMIT 5")
    rows = cur.fetchall()
    print("Users:", rows)
except Exception as e:
    print("Tabel users eroare:", e)

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
print("Tabele:", [r[0] for r in cur.fetchall()])
conn.close()
