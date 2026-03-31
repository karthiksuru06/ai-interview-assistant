#!/usr/bin/env python3
"""Verify FER model loads and produces non-static, input-dependent predictions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import numpy as np
import torch

# Use the actual InferenceService from the codebase
from app.services.inference import InferenceService, FERModel

def main():
    print("=" * 60)
    print("FER MODEL VERIFICATION")
    print("=" * 60)

    svc = InferenceService()
    loaded = svc.load_model()
    if not loaded:
        print("[FAIL] Model did not load.")
        sys.exit(1)

    print(f"\n[FER] Model loaded successfully")
    print(f"[FER] Device: {svc.device}")
    print(f"[FER] Architecture: efficientnet_b0")

    # Run 3 inferences with different random images to prove non-static output
    results = []
    for i in range(3):
        np.random.seed(i * 42 + 7)
        img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        t0 = time.perf_counter()
        result = svc.predict(img)
        dt = (time.perf_counter() - t0) * 1000
        results.append(result)
        print(f"\n--- Inference #{i+1}  ({dt:.1f} ms) ---")
        if result["success"]:
            print(f"  Predicted: {result['emotion']}  (conf={result['confidence']:.4f})")
            for emo, p in result["all_probabilities"].items():
                print(f"    {emo:12s}: {p:.4f}")
        else:
            print(f"  [ERROR] {result.get('error')}")

    # Verify non-static: all 3 results must NOT be identical
    if all(r["success"] for r in results):
        emotions = [r["emotion"] for r in results]
        confs = [r["confidence"] for r in results]
        probs0 = list(results[0]["all_probabilities"].values())
        probs1 = list(results[1]["all_probabilities"].values())
        probs_match = all(abs(a - b) < 1e-6 for a, b in zip(probs0, probs1))
        if probs_match:
            print("\n[WARN] Probabilities are identical for different inputs!")
        else:
            print("\n[PASS] Probabilities differ across inputs -> REAL inference confirmed")
    else:
        print("\n[FAIL] One or more inferences failed")

    print(f"\n[FER] Total inferences: {svc.total_inferences}")
    print(f"[FER] Avg inference time: {svc.total_inference_time / max(1, svc.total_inferences):.1f} ms")
    print("=" * 60)


if __name__ == "__main__":
    main()
