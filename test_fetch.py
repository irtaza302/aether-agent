import json
import urllib.request

req = urllib.request.Request("https://openrouter.ai/api/v1/models")
with urllib.request.urlopen(req, timeout=5) as response:
    data = json.loads(response.read().decode())
    print("Success, models count:", len(data.get("data", [])))
