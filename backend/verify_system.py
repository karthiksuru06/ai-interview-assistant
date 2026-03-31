"""
System Verification Script
==========================
Run this script to verify your environment is ready for submission.
"""

import os
import sys
import socket
import torch
from pathlib import Path

def print_status(component, status, details=""):
    symbol = "✅" if status else "❌"
    print(f"{symbol} {component:<20} {details}")

def check_gpu():
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print_status("GPU", True, f"{device_name} ({vram:.1f} GB VRAM)")
        return True
    else:
        print_status("GPU", False, "CUDA not available")
        return False

def check_files():
    base_path = Path(__file__).parent
    
    # Models
    models = [
        "models/best_model.pth",   # Video Model
        # "models/audio_best.pth"  # Audio Model (optional check if you have it)
    ]
    
    all_exist = True
    for model in models:
        path = base_path / model
        if path.exists():
            print_status("Model File", True, f"Found {model}")
        else:
            print_status("Model File", False, f"Missing {model}")
            all_exist = False
            
    return all_exist

def check_port(port):
    """Check if port is IN USE (meaning the app is likely running)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('127.0.0.1', port))
        if result == 0:
            return True # Port is open (App is running)
        else:
            return False # Port is closed (App is stopped)

def main():
    print("\n" + "="*50)
    print(" SMART AI ASSISTANT - SYSTEM VERIFICATION")
    print("="*50 + "\n")

    # 1. Hardware Check
    print("--- Hardware ---")
    gpu_ok = check_gpu()

    # 2. File Check
    print("\n--- Critical Files ---")
    files_ok = check_files()

    # 3. Service Status
    print("\n--- Service Status ---")
    backend_up = check_port(8000)
    frontend_up = check_port(5173)
    
    if backend_up:
        print_status("Backend API", True, "Running on port 8000")
    else:
        print_status("Backend API", False, "Not reachable (Port 8000 closed)")
        
    if frontend_up:
        print_status("Frontend UI", True, "Running on port 5173")
    else:
        print_status("Frontend UI", False, "Not reachable (Port 5173 closed)")

    # Final Summary
    print("\n" + "="*50)
    if gpu_ok and files_ok:
        print("RESULT: READY FOR SUBMISSION 🚀")
        if not backend_up or not frontend_up:
            print("(Note: Applications are currently stopped)")
    else:
        print("RESULT: ISSUES DETECTED ⚠️")
        print("Please resolve missing files or GPU issues.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
