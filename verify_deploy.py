import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request, ssl

ctx = ssl.create_default_context()
req = urllib.request.Request("https://ionut-analize-app-production.up.railway.app/")
with urllib.request.urlopen(req, context=ctx) as r:
    html = r.read().decode("utf-8")

scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
js = "\n".join(scripts)

with open("tmp_js_check.js", "w", encoding="utf-8") as f:
    f.write(js)

result = subprocess.run(
    ["node", "-e", "const fs=require('fs');try{new Function(fs.readFileSync('tmp_js_check.js','utf8'));console.log('JS OK');}catch(e){console.log('EROARE JS:',e.message);}"],
    capture_output=True, text=True
)
print(result.stdout.strip() or result.stderr.strip())
print("Lungime HTML:", len(html))
print("Are new-analiza-search:", "new-analiza-search" in html)
print("Are filtreazaAnalizeSearch:", "filtreazaAnalizeSearch" in html)
