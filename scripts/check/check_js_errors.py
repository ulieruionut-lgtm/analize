import urllib.request, ssl, re

ctx = ssl.create_default_context()
req = urllib.request.Request("https://ionut-analize-app-production.up.railway.app/")
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode("utf-8")

scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
total_js = "\n".join(scripts)
print("Numar blocuri script:", len(scripts))
print("Marime JS total:", len(total_js))

# Verifica functiile noi
for fn in ["filtreazaAnalizeSearch", "selecteazaAnaliza", "ascundeAnalizeSearch", "new-analiza-search"]:
    status = "OK" if fn in total_js or fn in html else "LIPSA"
    print(f"  [{status}]: {fn}")

# Salveaza JS pentru analiza manuala
with open("deployed_js.txt", "w", encoding="utf-8") as f:
    f.write(total_js)
print("\nJS salvat in deployed_js.txt")
print("Primele 200 caractere din primul script:")
if scripts:
    print(scripts[0][:200])
