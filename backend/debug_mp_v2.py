try:
    import mediapipe.python.solutions.face_mesh as mp_fm
    print("Successfully imported mediapipe.python.solutions.face_mesh")
    face_mesh = mp_fm.FaceMesh()
    print("Successfully created FaceMesh instance")
except Exception as e:
    print(f"Error: {e}")
