"""
Obtine DATABASE_URL pentru proiectul fd04b638 (vigilant-beauty) si ruleaza migrarile lipsa.
"""
import json, urllib.request, urllib.error

TOKEN = "rw_Fe26.2**91656300976a3918e335291c858d12f0a32a03346c2f0883dd55ad3f8db1f87a*nH-bQcaXEzD4P17eRe8TZw*QyKaQ-CK8MFxWIOJy0eiqRGt98WDgL56jeA4-4QoqyyBfBGiv65HEB_LYb6Kt0b0rilkKhuAS_gIGHKnFduXyQ*1774545386713*9b3d96efb8224b3d6be8fbb83dd28593d229161dd1ce07c7540e2ee7d1dae9c9*9V7RmhC8ntLuN9e84pTB5A-nbswtDx0UN-gidJF5MCk"
PROJECT_ID = "fd04b638-a858-45d0-b4fd-c70094cf4ce3"
ENV_ID = "55a3dfd5-ed8a-4ed6-8a3f-7d1a3e7c0d72"

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://backboard.railway.com/graphql/v2",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# Listeaza serviciile
q_services = """
query($projectId: String!) {
  project(id: $projectId) {
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
"""

try:
    resp = gql(q_services, {"projectId": PROJECT_ID})
    project = resp.get("data", {}).get("project", {})
    print(f"Project: {project.get('name')}")
    for edge in project.get("services", {}).get("edges", []):
        svc = edge["node"]
        print(f"  Service: {svc['id']} / {svc['name']}")
except Exception as e:
    print("Error listing services:", e)

# Incearca sa obtina variabilele de mediu
q_vars = """
query($projectId: String!, $environmentId: String!, $serviceId: String!) {
  variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
}
"""
