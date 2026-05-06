"""
Obtine DATABASE_URL pentru proiectul vigilant-beauty / serviciul web
prin Railway GraphQL API.
"""
import subprocess, json, os

# Obtine token din fisierul de configurare Railway
import pathlib

# Railway salveaza token-ul in ~\.railway\config.json pe Windows
config_paths = [
    pathlib.Path.home() / ".railway" / "config.json",
    pathlib.Path.home() / "AppData" / "Roaming" / "railway" / "config.json",
]

token = None
for p in config_paths:
    if p.exists():
        data = json.loads(p.read_text())
        token = data.get("token") or data.get("user", {}).get("token")
        if token:
            print(f"Token found in {p}")
            break

if not token:
    print("Token not found, checking env")
    token = os.environ.get("RAILWAY_TOKEN")

if not token:
    print("No token available")
else:
    print(f"Token: {token[:20]}...")
    
    import urllib.request, urllib.error
    
    # GraphQL query pentru variabilele serviciului
    query = """
    query {
      me {
        projects {
          edges {
            node {
              id
              name
              services {
                edges {
                  node {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://backboard.railway.com/graphql/v2",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            projects = resp.get("data", {}).get("me", {}).get("projects", {}).get("edges", [])
            for p in projects:
                proj = p["node"]
                print(f"\nProject: {proj['id']} / {proj['name']}")
                for s in proj.get("services", {}).get("edges", []):
                    svc = s["node"]
                    print(f"  Service: {svc['id']} / {svc['name']}")
    except Exception as e:
        print("GraphQL error:", e)
