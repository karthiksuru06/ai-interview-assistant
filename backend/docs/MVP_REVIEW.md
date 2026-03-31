# System Architecture & Implementation Review

### 1. Main System Functions (`main.py`)
The `main.py` file serves as a monolithic entry point for the MVP backend, adhering to a "Zero-Boilerplate" philosophy. It performs three critical functions:
*   **Infrastructure Initialization**: Configures the FastAPI application, CORS policies for frontend communication (specifically `localhost:5173`), and logging.
*   **Dependency Injection**: Instantiates the `FeedbackEngine` singleton via `get_feedback_engine`, isolating the AI logic from the HTTP transport layer.
*   **Request Orchestration**: The `/feedback` endpoint acts as a gateway that validates raw inputs using Pydantic models before delegating computation to the AI engine.

### 2. API Design Philosophy
The system exposes only **two endpoints**, reflecting a strict adherence to the Single Responsibility Principle for an academic prototype:
*   `GET /health`: A lightweight heartbeat for container orchestration and uptime monitoring.
*   `POST /feedback`: A stateless, synchronous endpoint that encapsulates the entire value proposition (analysis).
*   **Rationale**: By removing authentication, database persistence, and user management, the architecture focuses exclusively on the core novelty—multimodal AI analysis—without the "noise" of CRUD operations, which are trivial and distract from the research validation.

### 3. Gemini AI Integration
The `FeedbackEngine` wrapper encapsulates the stochastic nature of LLMs:
*   **Prompt Engineering**: It constructs a rigid JSON-schema instruction set, forcing Gemini to behave as a deterministic function (`(Input + Metrics) -> Structured Analysis`).
*   **Limitations**: The system currently relies on prompt-based JSON enforcement. A production iteration would utilize Gemini's "Structured Output" mode or a validation layer (like `instructor`) to guarantee schema compliance, preventing runtime parsing errors.

### 4. Error Handling & Reliability
*   **Graceful Degradation**: HTTP 500 errors are caught and logged, preventing stack traces from leaking to the client while preserving system stability.
*   **Environment Safety**: The system checks for `GEMINI_API_KEY` presence at startup, issuing warnings rather than crashing, to facilitate easier local debugging.

### 5. Academic MVP Justification
This implementation is **sufficient** because it validates the technical feasibility of the core hypothesis—that text descriptions of biometric data (eye contact, prosody) can be fused with semantic content analysis by an LLM to produce actionable coaching. Persistence, auth, and scaling are solved engineering problems; they add no research value to this specific proof-of-concept.

### 6. Out of Scope (Intentionally)
*   **Database**: Session history is ephemeral; the user is expected to consume feedback in real-time.
*   **Authentication**: The tool is designed as a single-user local tool or kiosk.
*   **Audio Processing**: Raw audio processing is assumed to happen upstream or client-side; this backend accepts pre-calculated metrics to keep latency deterministically low.
