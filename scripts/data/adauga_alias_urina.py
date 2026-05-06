import sys, psycopg2
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# IDs analize urinare (adaugate anterior)
# 284=pH urinar, 285=Densitate, 286=Proteine, 287=Glucoza,
# 288=Corpi cetonici, 289=Bilirubina, 290=Urobilinogen,
# 291=Nitriti, 292=Leucocite urina, 293=Hematii urina,
# 294=Bacterii, 297=Sediment

aliasuri = [
    # pH urinar
    ("LEUCOCITE URINARE",          292),
    ("LEUCOCITE URINARE ,",        292),
    ("Leucocite urinare",          292),
    ("LEUCOCITURIE",               292),
    # Nitriti
    ("NITRITI",                    291),
    ("NITRITI ,",                  291),
    ("Nitriti",                    291),
    ("Nitrituri",                  291),
    # Proteine
    ("PROTEINE TOTALE URINARE",    286),
    ("PROTEINE URINARE",           286),
    ("Proteine totale urinare",    286),
    ("PROTEINE,",                  286),
    # Bilirubina
    ("BILIRUBINA URINARA",         289),
    ("BILIRUBINA URINARA ,",       289),
    ("Bilirubina urinara",         289),
    # Densitate
    ("DENSITATE URINARA ,",        285),
    ("DENSITATE URINARA,",         285),
    # Corpi cetonici
    ("CORPI CETONICI",             288),
    ("CORPI CETONICI ,",           288),
    ("Corpi cetonici",             288),
    ("CETONE",                     288),
    # Eritrocite/Hematii
    ("ERITROCITE URINARE",         293),
    ("ERITROCITE URINARE ,",       293),
    ("Eritrocite urinare",         293),
    ("HEMATII URINARE",            293),
    # Glucoza
    ("GLUCOZA URINARA",            287),
    ("GLUCOZA URINARA ,",          287),
    ("Glucoza urinara",            287),
    # Urobilinogen
    ("UROBILINOGEN ,",             290),
    ("UROBILINOGEN,",              290),
    # Sediment
    ("Examenul sedimentului urinar", 297),
    ("SEDIMENT URINAR",            297),
    ("Sediment urinar",            297),
    ("EXAMEN SEDIMENT",            297),
    # Bacterii
    ("BACTERII",                   294),
    ("Bacterii",                   294),
]

print("Adaug aliasuri analize urinare:")
adaugate = 0
for alias, std_id in aliasuri:
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
    if cur.fetchone():
        print(f"  EXISTA: '{alias}'")
    else:
        cur.execute(
            "INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)",
            (alias, std_id)
        )
        print(f"  NOU: '{alias}' -> ID={std_id}")
        adaugate += 1

conn.commit()
print(f"\nTotal: {adaugate} aliasuri noi adaugate.")
conn.close()
