import sqlite3
import json
import os

DB_PATH = "interview.sqlite"

print("DATABASE INSPECTION")
print("=" * 50)

if not os.path.exists(DB_PATH):
    print(f"ERROR: Database file '{DB_PATH}' not found!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check users
cursor.execute("SELECT count(*) FROM users")
user_count = cursor.fetchone()[0]
print(f"\nTotal users: {user_count}")
print("\nUser details:")
print("-" * 50)

cursor.execute("SELECT data FROM users")
for row in cursor.fetchall():
    user = json.loads(row[0])
    print(f"Email: {user.get('email')}")
    print(f"Username: {user.get('username')}")
    print(f"Role: {user.get('role')}")
    print(f"Created: {user.get('created_at')}")
    print("-" * 50)

conn.close()
