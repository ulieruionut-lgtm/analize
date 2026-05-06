"""
Gaseste DATABASE_URL reala a aplicatiei web-production-2a2ad.up.railway.app
prin API GraphQL Railway.
"""
import subprocess, json

# Obtine token Railway din CLI
result = subprocess.run(["railway", "whoami"], capture_output=True, text=True, cwd="d:\\Ionut analize")
print("Whoami:", result.stdout.strip(), result.stderr.strip())

# Obtine toate proiectele si serviciile
result2 = subprocess.run(
    ["railway", "variables", "--json"],
    capture_output=True, text=True, cwd="d:\\Ionut analize"
)
print("Variables JSON:", result2.stdout[:500] if result2.stdout else result2.stderr[:200])
