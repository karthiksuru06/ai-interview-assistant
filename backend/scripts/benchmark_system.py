#!/usr/bin/env python3
"""
System Benchmark Script
=======================
Comprehensive performance testing including:
1. Model Latency (Audio & Video)
2. VRAM Usage
3. WebSocket Concurrency
"""

import sys
import time
import asyncio
import argparse
import statistics
import json
import base64
from pathlib import Path
from typing import Dict, List
import numpy as np
import torch
import torch.nn.functional as F
import websockets

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def get_vram_usage() -> Dict:
    """Get current GPU memory usage."""
    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}
    
    device = 0
    return {
        "allocated_gb": torch.cuda.memory_allocated(device) / (1024**3),
        "reserved_gb": torch.cuda.memory_reserved(device) / (1024**3),
        "max_allocated_gb": torch.cuda.max_memory_allocated(device) / (1024**3)
    }

def benchmark_models(iterations: int = 100) -> Dict:
    """Benchmark Video and Audio models latency."""
    print_header("MODEL LATENCY BENCHMARK")
    
    results = {}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # 1. Video Model (FER)
    try:
        from app.services.inference import get_inference_service
        service = get_inference_service()
        if service.load_model():
            print("\n[Video] Model loaded")
            model = service.model
            dummy_input = torch.randn(1, 3, 224, 224).to(device)
            
            # Warmup
            for _ in range(10):
                with torch.no_grad():
                    _ = model(dummy_input)
            
            # Benchmark
            latencies = []
            for _ in range(iterations):
                if device.type == 'cuda': torch.cuda.synchronize()
                start = time.perf_counter()
                with torch.no_grad():
                    _ = model(dummy_input)
                if device.type == 'cuda': torch.cuda.synchronize()
                latencies.append((time.perf_counter() - start) * 1000)
            
            avg_lat = statistics.mean(latencies)
            results['video_ms'] = avg_lat
            print(f"[Video] Average Latency: {avg_lat:.2f} ms")
    except Exception as e:
        print(f"[Video] Error: {e}")

    # 2. Audio Model
    try:
        from app.services.audio_inference import get_audio_inference_service
        audio_service = get_audio_inference_service()
        if audio_service.load_model():
            print("\n[Audio] Model loaded")
            audio_model = audio_service.model
            dummy_audio = torch.randn(1, 100, 40).to(device)
            
            # Warmup
            for _ in range(10):
                with torch.no_grad():
                    _ = audio_model(dummy_audio)
            
            # Benchmark
            latencies = []
            for _ in range(iterations):
                if device.type == 'cuda': torch.cuda.synchronize()
                start = time.perf_counter()
                with torch.no_grad():
                    _ = audio_model(dummy_audio)
                if device.type == 'cuda': torch.cuda.synchronize()
                latencies.append((time.perf_counter() - start) * 1000)
            
            avg_lat = statistics.mean(latencies)
            results['audio_ms'] = avg_lat
            print(f"[Audio] Average Latency: {avg_lat:.2f} ms")
    except Exception as e:
        print(f"[Audio] Error: {e}")
        
    return results

async def test_websocket_concurrency(num_clients: int = 5):
    """Test concurrent WebSocket connections."""
    print_header(f"WEBSOCKET CONCURRENCY TEST ({num_clients} Clients)")
    
    uri = f"ws://localhost:{settings.port}/interview/ws/test_session_{int(time.time())}"
    
    # Create a dummy base64 image (1x1 pixel)
    dummy_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    
    async def client_task(client_id: int):
        try:
            async with websockets.connect(uri) as websocket:
                start_time = time.perf_counter()
                
                # Send frame
                await websocket.send(dummy_img)
                
                # Wait for response
                response = await websocket.recv()
                data = json.loads(response)
                
                duration = (time.perf_counter() - start_time) * 1000
                return {
                    "id": client_id,
                    "status": "success",
                    "latency": duration,
                    "response": data.get("emotion")
                }
        except Exception as e:
            return {"id": client_id, "status": "error", "error": str(e)}

    # Run concurrent clients
    tasks = [client_task(i) for i in range(num_clients)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    avg_latency = statistics.mean([r["latency"] for r in results if r["status"] == "success"]) if success_count > 0 else 0
    
    print(f"Successful Connections: {success_count}/{num_clients}")
    print(f"Average Request Latency: {avg_latency:.2f} ms")
    
    for res in results:
        status = "OK" if res["status"] == "success" else "FAIL"
        info = f"{res['latency']:.2f}ms" if res["status"] == "success" else res.get("error")
        print(f"Client {res['id']}: [{status}] {info}")

def main():
    parser = argparse.ArgumentParser(description="System Performance Benchmark")
    parser.add_argument("--skip-concurrency", action="store_true", help="Skip WebSocket tests")
    args = parser.parse_args()

    # 1. Model & VRAM Benchmarks
    model_results = benchmark_models()
    
    vram = get_vram_usage()
    print_header("VRAM USAGE")
    if "error" not in vram:
        print(f"Allocated: {vram['allocated_gb']:.2f} GB")
        print(f"Max Allocated: {vram['max_allocated_gb']:.2f} GB")
    else:
        print(vram["error"])

    # 2. Concurrency Test
    if not args.skip_concurrency:
        try:
            asyncio.run(test_websocket_concurrency(5))
        except KeyboardInterrupt:
            pass
        except ConnectionRefusedError:
            print("\n[ERROR] Connection refused. Is the server running?")

if __name__ == "__main__":
    main()
