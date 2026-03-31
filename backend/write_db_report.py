import sqlite3
import json
import os

DB_PATH = "interview.sqlite"
OUTPUT_FILE = "db_report.txt"

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("DATABASE INSPECTION REPORT\n")
    f.write("=" * 60 + "\n\n")
    
    if not os.path.exists(DB_PATH):
        f.write(f"ERROR: Database file '{DB_PATH}' not found!\n")
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT count(*) FROM users")
        user_count = cursor.fetchone()[0]
        f.write(f"Total users in database: {user_count}\n\n")
        
        f.write("User Details:\n")
        f.write("-" * 60 + "\n")
        
        cursor.execute("SELECT data FROM users")
        for idx, row in enumerate(cursor.fetchall(), 1):
            user = json.loads(row[0])
            f.write(f"\nUser #{idx}:\n")
            f.write(f"  Email: {user.get('email')}\n")
            f.write(f"  Username: {user.get('username')}\n")
            f.write(f"  Role: {user.get('role')}\n")
            f.write(f"  Created: {user.get('created_at')}\n")
            f.write(f"  Has Password Hash: {'Yes' if user.get('hashed_password') else 'No'}\n")
        
        conn.close()
        f.write("\n" + "=" * 60 + "\n")

print(f"Report written to {OUTPUT_FILE}")
