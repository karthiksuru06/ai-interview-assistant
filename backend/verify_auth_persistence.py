import requests
import sqlite3
import json
import os

BASE_URL = "http://localhost:8000"
DB_PATH = "interview.sqlite"

def check_db_content():
    print(f"\n[DB CHECK] Inspecting {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print(f"FAILED: Database file {DB_PATH} not found!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check users table
        try:
            cursor.execute("SELECT count(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"SUCCESS: Users table found. Total users: {user_count}")
            
            cursor.execute("SELECT data FROM users")
            rows = cursor.fetchall()
            print("   User entries:")
            for row in rows:
                data = json.loads(row[0])
                print(f"   - {data.get('email')} (Role: {data.get('role')})")
        except sqlite3.OperationalError:
            print("FAILED: 'users' table not found in database!")

        conn.close()
    except Exception as e:
        print(f"FAILED: Database inspection failed: {e}")

def verify_api_flow():
    print("\n[API CHECK] Testing Auth Flow...")
    
    # 1. Test Admin Login
    print("\n1. Testing Admin Login...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@smartai.com",
            "password": "admin"
        })
        if resp.status_code == 200:
            print("SUCCESS: Admin login successful")
        else:
            print(f"FAILED: Admin login failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"FAILED: Connection failed: {e}")
        return

    # 2. Test Signup
    print("\n2. Testing New User Signup...")
    new_user = {
        "username": "verify_user_1",
        "email": "verify1@example.com",
        "password": "password123",
        "security_question": "test?",
        "security_answer": "answer"
    }
    
    resp = requests.post(f"{BASE_URL}/auth/signup", json=new_user)
    if resp.status_code == 200:
        print("SUCCESS: Signup successful")
    elif resp.status_code == 400 and "already registered" in resp.text:
         print("WARNING: User already exists (skipping signup)")
    else:
        print(f"FAILED: Signup failed: {resp.status_code} - {resp.text}")

    # 3. Test New User Login
    print("\n3. Testing New User Login...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": new_user["email"],
        "password": new_user["password"]
    })
    if resp.status_code == 200:
        print("SUCCESS: New user login successful")
    else:
        print(f"FAILED: New user login failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    verify_api_flow()
    check_db_content()
