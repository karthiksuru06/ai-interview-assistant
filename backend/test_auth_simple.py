import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("AUTH FLOW VERIFICATION")
print("=" * 60)

# Test 1: Admin Login
print("\n[TEST 1] Admin Login")
print("-" * 40)
try:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@smartai.com", "password": "admin"}
    )
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Result: SUCCESS")
        print(f"Token received: {data.get('access_token')[:20]}...")
        print(f"Role: {data.get('role')}")
    else:
        print(f"Result: FAILED")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"Result: ERROR - {e}")

# Test 2: Signup New User
print("\n[TEST 2] New User Signup")
print("-" * 40)
try:
    resp = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "username": "testuser123",
            "email": "testuser123@example.com",
            "password": "testpass123",
            "security_question": "What is your favorite color?",
            "security_answer": "blue"
        }
    )
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Result: SUCCESS - User created")
    elif resp.status_code == 400:
        print(f"Result: User already exists (expected if run multiple times)")
    else:
        print(f"Result: FAILED")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"Result: ERROR - {e}")

# Test 3: Login with New User
print("\n[TEST 3] New User Login")
print("-" * 40)
try:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "testuser123@example.com", "password": "testpass123"}
    )
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Result: SUCCESS")
        print(f"Token received: {data.get('access_token')[:20]}...")
        print(f"Role: {data.get('role')}")
    else:
        print(f"Result: FAILED")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"Result: ERROR - {e}")

# Test 4: Check Database
print("\n[TEST 4] Database Check")
print("-" * 40)
import sqlite3
import os

DB_PATH = "interview.sqlite"
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"Total users in database: {count}")
    
    cursor.execute("SELECT data FROM users")
    for row in cursor.fetchall():
        user_data = json.loads(row[0])
        print(f"  - {user_data.get('email')} (role: {user_data.get('role')})")
    conn.close()
else:
    print(f"Database file not found: {DB_PATH}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
