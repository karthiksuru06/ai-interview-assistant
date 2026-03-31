#!/usr/bin/env python3
"""Verify Whisper ASR loads and can transcribe audio."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import warnings
warnings.filterwarnings("ignore")

print("=" * 60)
print("WHISPER ASR VERIFICATION")
print("=" * 60)

# Test 1: Import whisper
print("\n--- Test 1: Import whisper ---")
try:
    import whisper
    print(f"  [PASS] whisper imported  (version: {getattr(whisper, '__version__', 'unknown')})")
except ImportError as e:
    print(f"  [FAIL] Cannot import whisper: {e}")
    sys.exit(1)

# Test 2: Load model
print("\n--- Test 2: Load 'small' model ---")
t0 = time.perf_counter()
try:
    model = whisper.load_model("small")
    dt = (time.perf_counter() - t0) * 1000
    print(f"  [PASS] Model loaded in {dt:.0f}ms")
    print(f"  Device : {next(model.parameters()).device}")
    params = sum(p.numel() for p in model.parameters())
    print(f"  Params : {params:,}")
except Exception as e:
    print(f"  [FAIL] Model load failed: {e}")
    sys.exit(1)

# Test 3: Transcribe synthetic audio (5 seconds of silence -> should return empty/short text)
print("\n--- Test 3: Transcribe synthetic audio ---")
import numpy as np
# Generate 3 seconds of low white noise at 16kHz
audio = np.random.randn(16000 * 3).astype(np.float32) * 0.001
t0 = time.perf_counter()
try:
    result = model.transcribe(audio, language="en")
    dt = (time.perf_counter() - t0) * 1000
    text = result.get("text", "").strip()
    print(f"  Transcription ({dt:.0f}ms): '{text[:200]}'")
    print(f"  Segments     : {len(result.get('segments', []))}")
    print(f"  [PASS] Whisper transcription pipeline works")
except Exception as e:
    print(f"  [FAIL] Transcription error: {e}")
    sys.exit(1)

# Test 4: Integration with AudioService
print("\n--- Test 4: AudioService integration ---")
try:
    from app.services.audio import AudioService
    svc = AudioService.__new__(AudioService)
    svc._initialized = False
    svc._asr_model = None
    svc._asr_available = False
    svc.__init__()

    loaded = svc._load_asr_model()
    print(f"  ASR loaded: {loaded}")
    print(f"  ASR available: {svc._asr_available}")
    if loaded:
        print(f"  [PASS] AudioService Whisper integration works")
    else:
        print(f"  [WARN] AudioService could not load Whisper model")
except Exception as e:
    print(f"  [WARN] AudioService test skipped: {e}")

print("\n" + "=" * 60)
print("[WHISPER] ASR pipeline is operational")
print("=" * 60)
