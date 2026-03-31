import requests
import json

BASE_URL = "http://localhost:8000"
OUTPUT_FILE = "api_test_report.txt"

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("API AUTHENTICATION TEST REPORT\n")
    f.write("=" * 60 + "\n\n")
    
    # Test 1: Admin Login
    f.write("TEST 1: Admin Login\n")
    f.write("-" * 60 + "\n")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "admin@smartai.com", "password": "admin"},
            timeout=5
        )
        f.write(f"Status Code: {resp.status_code}\n")
        f.write(f"Response Headers: {dict(resp.headers)}\n")
        f.write(f"Response Body: {resp.text}\n")
        
        if resp.status_code == 200:
            data = resp.json()
            f.write(f"\nRESULT: SUCCESS\n")
            f.write(f"Access Token (first 30 chars): {data.get('access_token', '')[:30]}...\n")
            f.write(f"Token Type: {data.get('token_type')}\n")
            f.write(f"Role: {data.get('role')}\n")
        else:
            f.write(f"\nRESULT: FAILED\n")
    except Exception as e:
        f.write(f"\nRESULT: ERROR\n")
        f.write(f"Exception: {str(e)}\n")
    
    f.write("\n" + "=" * 60 + "\n\n")
    
    # Test 2: Signup
    f.write("TEST 2: New User Signup\n")
    f.write("-" * 60 + "\n")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/signup",
            json={
                "username": "testuser999",
                "email": "testuser999@example.com",
                "password": "testpass123",
                "security_question": "What is your favorite color?",
                "security_answer": "blue"
            },
            timeout=5
        )
        f.write(f"Status Code: {resp.status_code}\n")
        f.write(f"Response Body: {resp.text}\n")
        
        if resp.status_code == 200:
            f.write(f"\nRESULT: SUCCESS - User created\n")
        elif resp.status_code == 400 and "already" in resp.text.lower():
            f.write(f"\nRESULT: User already exists (expected if run before)\n")
        else:
            f.write(f"\nRESULT: FAILED\n")
    except Exception as e:
        f.write(f"\nRESULT: ERROR\n")
        f.write(f"Exception: {str(e)}\n")
    
    f.write("\n" + "=" * 60 + "\n\n")
    
    # Test 3: New User Login
    f.write("TEST 3: New User Login\n")
    f.write("-" * 60 + "\n")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "testuser999@example.com", "password": "testpass123"},
            timeout=5
        )
        f.write(f"Status Code: {resp.status_code}\n")
        f.write(f"Response Body: {resp.text}\n")
        
        if resp.status_code == 200:
            data = resp.json()
            f.write(f"\nRESULT: SUCCESS\n")
            f.write(f"Role: {data.get('role')}\n")
        else:
            f.write(f"\nRESULT: FAILED\n")
    except Exception as e:
        f.write(f"\nRESULT: ERROR\n")
        f.write(f"Exception: {str(e)}\n")
    
    f.write("\n" + "=" * 60 + "\n")

print(f"API test report written to {OUTPUT_FILE}")
