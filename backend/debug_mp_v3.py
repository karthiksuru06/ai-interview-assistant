import mediapipe as mp
try:
    from mediapipe.python.solutions import face_mesh
    print("Found face_mesh in mediapipe.python.solutions")
except ImportError:
    print("NOT found in mediapipe.python.solutions")

try:
    import mediapipe.solutions.face_mesh
    print("Found face_mesh in mediapipe.solutions")
except ImportError:
    print("NOT found in mediapipe.solutions")

print(f"Mediapipe dir: {dir(mp)}")
