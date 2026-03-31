import mediapipe as mp
import os
with open("mp_dir.txt", "w") as f:
    f.write(f"Mediapipe version: {mp.__version__}\n")
    f.write(f"Mediapipe path: {mp.__file__}\n")
    f.write(f"Mediapipe dir: {dir(mp)}\n")
