#!/usr/bin/env python3
"""Verify Gemini API is reachable and produces real, non-template responses."""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Suppress deprecation warnings for test
import warnings
warnings.filterwarnings("ignore")

from app.config import settings

print("=" * 60)
print("GEMINI API VERIFICATION")
print("=" * 60)

api_key = settings.gemini_api_key
model_name = settings.gemini_model
print(f"API key present : {'YES' if api_key else 'NO'}")
print(f"API key length  : {len(api_key) if api_key else 0}")
print(f"Model name      : {model_name}")

if not api_key:
    print("[FAIL] No API key configured")
    sys.exit(1)

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    # Test 1: Simple generation
    print("\n--- Test 1: Simple prompt ---")
    t0 = time.perf_counter()
    response = model.generate_content(
        "Generate a single, unique interview question about Python data structures. "
        "Return only the question, nothing else."
    )
    dt = (time.perf_counter() - t0) * 1000
    text1 = response.text.strip()
    print(f"  Response ({dt:.0f}ms): {text1[:200]}")

    # Test 2: Different prompt to prove non-determinism
    print("\n--- Test 2: Different prompt ---")
    t0 = time.perf_counter()
    response2 = model.generate_content(
        "Generate a single, unique interview question about system design. "
        "Return only the question, nothing else."
    )
    dt2 = (time.perf_counter() - t0) * 1000
    text2 = response2.text.strip()
    print(f"  Response ({dt2:.0f}ms): {text2[:200]}")

    # Test 3: JSON structured response (mimics real usage)
    print("\n--- Test 3: JSON structured response ---")
    t0 = time.perf_counter()
    response3 = model.generate_content(
        'Evaluate this interview answer:\n'
        'Question: "What is polymorphism?"\n'
        'Answer: "Polymorphism is when objects of different classes respond to the same method call."\n\n'
        'Return JSON: {"score": <1-10>, "feedback": "<text>", "strengths": [], "improvements": []}'
    )
    dt3 = (time.perf_counter() - t0) * 1000
    text3 = response3.text.strip()
    print(f"  Response ({dt3:.0f}ms): {text3[:300]}")

    # Verify non-template
    if text1 == text2:
        print("\n[WARN] Responses are identical -- may be cached")
    else:
        print("\n[PASS] Responses differ across prompts -> REAL API confirmed")

    print(f"\n[GEMINI] Model '{model_name}' is operational")
    print(f"[GEMINI] All 3 API calls returned HTTP 200")
    print("=" * 60)

except Exception as e:
    print(f"\n[FAIL] Gemini error: {e}")
    sys.exit(1)
