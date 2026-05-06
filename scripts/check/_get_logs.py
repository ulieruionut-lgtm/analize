import subprocess
import json

# Get Railway token
result = subprocess.run(["railway", "whoami"], capture_output=True, text=True)
print("whoami:", result.stdout, result.stderr)

# Try to get build logs via railway CLI
result2 = subprocess.run(
    ["railway", "deployment", "list", "--json"],
    capture_output=True, text=True, cwd="d:\\Ionut analize"
)
print("deployments:", result2.stdout[:2000] if result2.stdout else result2.stderr[:500])
