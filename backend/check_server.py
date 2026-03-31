import requests

BASE_URL = "http://localhost:8000"
OUTPUT_FILE = "server_check.txt"

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("SERVER STATUS CHECK\n")
    f.write("=" * 60 + "\n\n")
    
    # Check root
    f.write("Checking root endpoint /\n")
    f.write("-" * 60 + "\n")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        f.write(f"Status: {resp.status_code}\n")
        f.write(f"Response: {resp.text}\n\n")
    except Exception as e:
        f.write(f"ERROR: {e}\n\n")
    
    # Check OpenAPI docs
    f.write("Checking /openapi.json\n")
    f.write("-" * 60 + "\n")
    try:
        resp = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        f.write(f"Status: {resp.status_code}\n")
        if resp.status_code == 200:
            data = resp.json()
            f.write(f"\nRegistered paths:\n")
            for path in sorted(data.get('paths', {}).keys()):
                f.write(f"  {path}\n")
        else:
            f.write(f"Response: {resp.text}\n")
    except Exception as e:
        f.write(f"ERROR: {e}\n")
    
    f.write("\n" + "=" * 60 + "\n")

print(f"Server check written to {OUTPUT_FILE}")
