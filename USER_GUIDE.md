# User Guide — Smart AI Interview Assistant

> A step-by-step guide for users to navigate the platform.

---

## How to Run the Application

### Step 1: Start the Backend
1. Open a **Terminal**
2. Navigate to `backend`:
   ```powershell
   cd backend
   ```
3. Activate environment and run:
   ```powershell
   .\venv\Scripts\activate
   python run.py
   ```
   Backend runs at **http://localhost:8000** | API docs at **http://localhost:8000/docs**

### Step 2: Start the Frontend
1. Open a **NEW** Terminal
2. Navigate to `frontend`:
   ```powershell
   cd frontend
   ```
3. Run:
   ```powershell
   npm run dev
   ```
   Frontend runs at **http://localhost:5173**

### Step 3: Open the App
Navigate to `http://localhost:5173` in Chrome or Edge.

---

## Creating an Account

1. Click **"Sign Up"** on the login page
2. Fill in your email, username, password, and a security question
3. Click **"Create Account"**
4. You will be logged in and taken to the Dashboard

### Forgot Your Password?
1. Click **"Forgot Password?"** on the login page
2. Enter your email and answer the security question you set during signup
3. Set a new password

---

## Dashboard — Choose Your Interview

After logging in, configure your interview:

1. **Select a Subject** — Software Engineering, HR, Data Science, Product Management, ML, or General
2. **Select Difficulty** — Easy, Medium, or Hard
3. **Enter Job Role** — e.g., "Senior Frontend Developer"
4. Click **"Start Interview"**

---

## The Interview Session

### Camera Feed (Left Side)
- Your live webcam feed with an overlay showing:
  - **Current Emotion** — The AI detects your facial expression in real-time
  - **Confidence Score** — How confident the AI is about the detected emotion
  - **Recording Indicator** — A red "REC" dot when the session is active

### Question Display (Top)
- The current question appears in a large glowing box
- The question type (Technical / Behavioural / Situational) is shown as a badge
- If **Text-to-Speech** is enabled, the question will be read aloud

### Controls
- **Microphone Toggle** — Click the mic button to mute/unmute
- **TTS Toggle** — Click the speaker button to enable/disable question reading
- **Next Question** — After answering, click to get the next question
- **End Session** — Click when you are done to see your results

### Live Transcript (Right Side)
- A scrolling log showing:
  - Questions asked (in cyan)
  - Your answers (in purple)
  - AI feedback (in green)

### How to Answer
1. Read (or listen to) the question
2. Click **"Start Answering"** when ready
3. Speak your answer clearly into the microphone
4. Click **"Submit Answer"** when finished
5. Review the AI feedback, then click **"Next Question"**

### Tips for Best Results
- **Good lighting** — Make sure your face is well-lit
- **Steady camera** — Position your webcam at eye level
- **Quiet environment** — Background noise affects voice clarity scores
- **Look at the camera** — The AI tracks eye contact
- **Speak clearly** — Avoid filler words like "um" and "uh"

---

## End of Session

When you click **"End Session"**, the AI generates a summary:

- **Overall Score** — Your performance rating out of 10
- **Performance Rating** — Excellent / Good / Average / Needs Improvement
- **Recommendations** — Specific areas to improve
- **Duration** — How long the interview lasted
- **Total Questions** — Number of questions answered

You will be redirected to the **History** page.

---

## Review Your History

The **History** page shows all your past interview sessions:

1. Each session card shows the role, date/time, and score (colour-coded)
2. Click a card to expand and see individual question scores, your answers, and AI feedback
3. Click **"Download PDF"** to save a formatted report

---

## Question Bank (Study Material)

The **Question Bank** page provides curated interview questions:

1. Select a tab: **Python**, **Java**, or **HR**
2. Browse questions sorted by difficulty (Easy / Medium / Hard)
3. Click the **eye icon** to reveal the answer, tips, and detailed explanations

---

## Navigation

| Page | URL | What It Does |
|------|-----|--------------|
| Login | `/login` | Sign in to your account |
| Signup | `/signup` | Create a new account |
| Dashboard | `/dashboard` | Configure and start interviews |
| Interview | `/session` | Live AI-powered interview |
| History | `/history` | Review past sessions + PDF export |
| Question Bank | `/question-bank` | Study curated questions |
| Admin | `/admin` | Platform statistics (admin only) |

---

## Troubleshooting

### "Camera not working"
- Make sure you have given browser permission to access the camera
- Check that no other app is using the camera (Zoom, Teams, etc.)
- Try refreshing the page

### "Microphone not detected"
- Check browser permissions for microphone access
- Make sure your mic is not muted at the system level
- Try a different browser (Chrome works best)

### "Blank screen"
- Open browser Developer Tools (F12) and check the Console tab for errors
- Make sure both backend and frontend servers are running

### "Questions not loading"
- Check that the backend is running and connected to the database
- Verify the `GEMINI_API_KEY` is set in the backend `.env` file

### "No emotion detection"
- The FER model needs a GPU for real-time performance (or `AI_SAFE_MODE=true` for mock data)
- Ensure good lighting so the AI can see your face clearly
- Make sure only one face is in frame
