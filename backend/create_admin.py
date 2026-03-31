"""
Create Admin User Script
========================
Run this script to create an admin user with username 'admin' and password 'admin'.

Usage:
    python create_admin.py
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app import database
from app.routers.auth import hash_password


async def create_admin_user():
    """Create admin user if not exists."""
    
    print("[*] Connecting to database...")
    await database.init_database()
    
    # Check if admin already exists
    existing_admin = await database.users_collection.find_one({"username": "admin"})
    
    if existing_admin:
        print("[!] Admin user already exists.")
        print(f"    Username: admin")
        print(f"    Role: {existing_admin.get('role', 'unknown')}")
        
        # Update to admin role if not already
        if existing_admin.get("role") != "admin":
            await database.users_collection.update_one(
                {"_id": existing_admin["_id"]},
                {"$set": {"role": "admin"}}
            )
            print("[+] Updated user role to ADMIN")
        
    else:
        # Create new admin user
        from datetime import datetime
        admin_doc = {
            "username": "admin",
            "email": "admin@smartai.com",
            "hashed_password": hash_password("admin"),
            "security_question": "What is the admin password?",
            "security_answer_hash": hash_password("admin"),
            "role": "admin",
            "created_at": datetime.utcnow()
        }
        
        await database.users_collection.insert_one(admin_doc)

        print("[+] Admin user created successfully!")
        print(f"    Username: admin")
        print(f"    Password: admin")
        print(f"    Email: admin@smartai.com")
        print(f"    Role: admin")
    
    await database.close_database()


if __name__ == "__main__":
    print("=" * 50)
    print("Smart AI Interview Assistant - Admin Setup")
    print("=" * 50)
    asyncio.run(create_admin_user())
    print("=" * 50)
    print("You can now login at http://localhost:5173/login")
    print("=" * 50)
