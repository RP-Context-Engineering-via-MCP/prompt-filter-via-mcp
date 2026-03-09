import requests
import json
import uuid

PORT = 3004
URL = f"http://localhost:{PORT}/enrich"

payload = {
    "prompt": "I prefer dark mode and use Python for most of my projects",
    "user_id": "5ca4d3ee-a139-44f9-9f9a-84655025a8f2",
    "session_id": "61b0cb8b-1cf1-4034-b623-c0cdd4bb16d5",
    "source": "mcp",
    "mcp_client": "claude_desktop"
}

print(f"Testing MCP SOURCE {URL} ...")
try:
    response = requests.post(URL, json=payload, timeout=20)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

print("\n-----------------------\n")

payload["source"] = "web_client"
print(f"Testing WEB CLIENT SOURCE {URL} ...")
try:
    response = requests.post(URL, json=payload, timeout=20)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
