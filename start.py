import os
import subprocess

port = os.environ.get("PORT", "8000")
subprocess.run(["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", port])
