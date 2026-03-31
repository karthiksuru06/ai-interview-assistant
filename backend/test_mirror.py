"""
AI Interview - Perfect Mirror & Metrics Test
============================================
Utility script for local verification of facial tracking and emotion detection.
Uses the 'fer' library (suggested by friend) and MediaPipe.
"""

import cv2
import time
import numpy as np
import mediapipe as mp
from fer import FER

def main():
    print("Initializing AI Engine (Perfect Mirror)...")
    
    # FER (Facial Emotion Recognition)
    try:
        # mtcnn=False is better for real-time fluidity on CPU
        detector = FER(mtcnn=False)
        print("[AI] FER Library initialized (Haar Cascade mode for speed)")
    except Exception as e:
        print(f"[AI] FER Error: {e}")
        return

    # MediaPipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Video Capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Could not open webcam.")
        return

    print("--- [SMART AI INTERVIEW] Perfect Mirror Mode ACTIVE ---")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Mirror for natural view
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # 1. Detect Emotion with FER
        start_time = time.perf_counter()
        results = detector.detect_emotions(frame)
        fer_latency = (time.perf_counter() - start_time) * 1000

        if results:
            data = results[0]
            emotions = data["emotions"]
            dominant = max(emotions, key=emotions.get)
            score = emotions[dominant]
            box = data["box"] # [x, y, w, h]
            
            # Draw Bounding Box (Cyan theme for Smart AI)
            x, y, bw, bh = box
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), (212, 182, 6), 2) # BGR
            
            # Draw Label
            label = f"{dominant.upper()} {int(score*100)}%"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (212, 182, 6), 2)
            
            # Draw Confidence Bar
            cv2.rectangle(frame, (10, h-40), (210, h-20), (50, 50, 50), -1)
            cv2.rectangle(frame, (10, h-40), (10+int(score*200), h-20), (212, 182, 6), -1)
            cv2.putText(frame, "AI Confidence", (10, h-50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 2. Face Mesh (for Metrics)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_results = face_mesh.process(rgb)
        
        if mp_results.multi_face_landmarks:
            # Subtle points for "High Tech" feel
            for landmarks in mp_results.multi_face_landmarks:
                for idx in [33, 263, 1, 61, 291]: # Just a few key points
                    px = int(landmarks.landmark[idx].x * w)
                    py = int(landmarks.landmark[idx].y * h)
                    cv2.circle(frame, (px, py), 2, (0, 255, 255), -1)

        # UI Overlay
        cv2.putText(frame, f"Latency: {int(fer_latency)}ms", (w-150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, "PRO AI ENGINE", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

        cv2.imshow('AI Interview - Smart Mirror Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Terminated.")

if __name__ == "__main__":
    main()
