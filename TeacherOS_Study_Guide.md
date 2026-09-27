# TeacherOS Project Study Guide (Sprint 5)

This study guide covers the entire architecture, API design, folder structure, and the transition/improvements from Sprint 4 (Phase 1) to Sprint 5 (Phase 2). Use this document to prepare thoroughly for your technical review.

## 1. Project Overview & Evolution

**Phase 1 (Sprint 4) - The Foundation:**
- We built a FastAPI-based backend integrated with an SQLite/PostgreSQL database.
- We created a pure HTML/JS frontend (Vanilla web stack, no complex frameworks like React/Next.js) to keep things lightweight.
- We implemented core features: User Authentication, Curriculum Generation & Enhancement (via standard LLM calls), basic Chatbot, and legacy Assessment generation.
- Implemented RAG (Retrieval-Augmented Generation) for indexing syllabus files and answering chat queries based on the syllabus.

**Phase 2 (Sprint 5) - Agentic Workflows (The Major Improvement):**
- We introduced **LangGraph** to replace basic LLM calls with robust, stateful **Agents**.
- **Curriculum Agent**: Added a **Human-In-The-Loop (HITL)** architecture. Instead of just generating and saving, the agent pauses (using a PostgreSQL Checkpointer to save its state), asks the teacher for approval/clarification, and resumes based on human feedback.
- **Assessment Agent**: Upgraded to a parallel architecture with **Bounded Retries**. It can now generate multiple test variations at once (batches), auto-validate the questions, and retry internally if a question is invalid.
- **Unified Endpoints**: We refactored Curriculum Generation to happen in single, unified API calls (handling DB record creation, file upload, indexing, AI generation, and saving all in one go).

---

## 2. Folder Structure & Responsibilities

The codebase is highly modularized, following a clean architecture pattern:

* **`backend/`**: Contains the core FastAPI application.
  * **`main.py`**: The entry point. Initializes the app, sets up CORS, connects the LangGraph PostgreSQL checkpointer, mounts the static frontend, and includes all routers.
  * **`database.py`**: Manages the SQLAlchemy database engine, sessions, and safe migrations.
  * **`models.py`**: Defines the SQLAlchemy database models (`User`, `Curriculum`, `CurriculumWeek`, etc.).
  * **`schemas.py`**: Pydantic models for data validation (defines the structure of API requests and responses).
  * **`auth.py`**: Handles password hashing, verification, and JWT token creation.
  * **`routers/`**: The controllers of the application. Contains all the API endpoints grouped by feature (see Section 3).

* **`frontend/`**: Contains the Vanilla HTML, CSS, and JS files. 
  * Files like `curriculum-agent.html` and `assessment-agent.html` were added in Sprint 5 to interface with the new agentic endpoints.

* **`rag/`**: Contains logic for Retrieval-Augmented Generation.
  * **`chunker.py`**: Splits syllabus files into readable chunks.
  * **`embeddings.py`**: Interfaces with the AI embedding model.
  * **`vector_store.py`**: Manages the ChromaDB vector database.
  * **`indexer.py`**: Orchestrates taking a file, chunking it, embedding it, and saving it to ChromaDB.
  * **`retriever.py` / `rag_pipeline.py`**: Fetches relevant chunks for Chat queries.

* **`agents/`**: Contains the Phase 2 LangGraph agent logic.
  * **`graph.py`**: Builds the `StateGraph` for both Curriculum and Assessment agents (defining nodes and conditional edges).
  * **`state.py`**: Defines the typed state dictionaries (`CurriculumAgentState`, `AssessmentAgentState`) that get passed between nodes.
  * **`curriculum_agent.py` & `assessment_agent.py`**: The actual node functions (the "thinking" steps) for the graphs.
  * **`memory.py`**: Manages conversational memory for the agents.
  * **`tools.py`**: Helper functions for the agents to interact with the database.

* **`data/`**: Stores uploads and the local ChromaDB/SQLite files.

---

## 3. Comprehensive API Breakdown

Here is a list of every API created, categorized by their router file:

### A. Authentication (`backend/routers/auth.py`)
- **`POST /auth/register`**: Registers a new user. Hashes the password and saves to DB.
- **`POST /auth/login`**: Authenticates a user and returns a JWT Bearer token.
- **`GET /auth/me`**: Returns the currently logged-in user's details based on the JWT token.

### B. Curriculum (Phase 1 & Unified) (`backend/routers/curriculum.py`)
- **`POST /curriculums`**: Manually creates a curriculum record.
- **`GET /curriculums`**: Lists all curricula for the logged-in user.
- **`GET /curriculums/{id}`**: Gets details of a specific curriculum.
- **`GET /curriculums/{id}/weeks`**: Fetches the week-by-week plan for a curriculum.
- **`POST /curriculums/generate` (Unified - Sprint 5)**: Creates a new curriculum, uploads/saves the syllabus, indexes it to ChromaDB, runs the AI generation, and saves the weeks all in one call.
- **`POST /curriculums/enhance` (Unified - Sprint 5)**: Similar to generation, but takes an *existing* curriculum file, analyzes gaps, and generates an improved version.
- **`POST /curriculums/{id}/generate` (Legacy)**: The old Phase 1 generation endpoint (kept for backward compatibility).
- **`PUT /curriculums/{id}/weeks/{week_id}`**: Updates a specific week's content manually.
- **`GET /curriculums/{id}/export`**: Exports the curriculum into an Excel (`.xlsx`) file.
- **`DELETE /curriculums/{id}`**: Deletes the curriculum, its weeks, files, and removes its embeddings from ChromaDB.

### C. Dashboard (`backend/routers/dashboard.py`)
- **`GET /dashboard/{id}`**: Calculates statistics for the dashboard (total weeks, completed weeks, progress percentage, next topic, next assessment).

### D. Chat / RAG (`backend/routers/chat.py`)
- **`POST /chat`**: Takes a user query, identifies if it needs theory, exercises, or answers, retrieves up to 8 relevant chunks from ChromaDB, and uses the LLM to generate an answer.

### E. File Management (`backend/routers/files.py`)
- **`POST /files/upload`**: Dedicated endpoint to upload a syllabus PDF/DOCX and index it into the RAG system.

### F. Legacy Assessment (`backend/routers/assessment.py`)
- **`POST /assessments/generate`**: The basic Phase 1 assessment generation.
- **`POST /assessments/replace`**: Replaces a specific question in a generated assessment.

### G. Phase 2 Agents (`backend/routers/agents.py`) - *The Core of Sprint 5*
**Curriculum Agent (HITL):**
- **`POST /agents/curriculum/run`**: Starts the LangGraph Curriculum Agent. Generates a unique `thread_id`. The graph pauses (Interrupts) to ask the user for approval/clarification.
- **`POST /agents/curriculum/{thread_id}/resume`**: Resumes the paused agent with the user's decision (`approved`, `rejected`, `modify`) and any extra instructions.
- **`GET /agents/curriculum/{thread_id}/status`**: Checks if the agent thread is completed or awaiting input.
- **`GET /agents/curriculum/{id}/memories`**: Retrieves the agent's memory history for a curriculum.

**Assessment Agent (Parallel/Batching):**
- **`POST /agents/assessment/generate`**: Starts the Assessment Agent. Generates multiple variations (batches) concurrently, auto-validates them, and saves them to the DB.
- **`GET /agents/assessment/batches`**: Lists all generated assessment batches for a curriculum.
- **`GET /agents/assessment/batches/{id}`**: Gets a specific batch and all its question variations.
- **`DELETE /agents/assessment/batches/{id}`**: Deletes a batch.
- **`GET /agents/assessment/{id}`**: Gets a single specific assessment variation.
- **`GET /agents/assessment/{id}/export/question-paper`**: Exports the assessment as a formatted HTML Question Paper (with MathJax for math symbols).
- **`GET /agents/assessment/{id}/export/answer-key`**: Exports the Answer Key as formatted HTML.
- **`GET /agents/assessment/batches/{id}/export/zip`**: Exports an entire batch of assessments into a downloadable ZIP file.

---

## 4. How Agents Work & How Things Are Identified

### The Curriculum Agent (Human-in-the-Loop)
1. **State:** Uses `CurriculumAgentState` to pass data (user request, syllabus context, proposed changes, human decision) between nodes.
2. **Graph:** The agent starts -> loads memory -> plans changes -> **Pauses (Interrupt)**. 
3. **Checkpointer:** We use LangGraph's `PostgresSaver`. When the graph pauses, the state is saved to the PostgreSQL DB. The API returns the proposed changes to the frontend.
4. **Resumption:** The frontend sends the user's feedback to the `/resume` endpoint. The graph loads the state from PostgreSQL, applies changes (or replans), and finishes.

### The Assessment Agent (Parallel & Self-Healing)
1. **State:** Uses `AssessmentAgentState` tracking total questions, difficulty distribution, and a list of `VariationResult`.
2. **Graph:** It creates a blueprint -> Generates variations. 
3. **Self-Correction:** It includes a `validate` node. If a generated question doesn't match the required difficulty or format, it triggers a `retry_failed` node which regenerates the specific bad question before saving the final batch.

### RAG and "Identifying Things"
When answering chat queries or giving agents context, the RAG system identifies context intelligently:
- The syllabus is split into chunks (`chunker.py`) and embedded using an AI model.
- During a chat, `retriever.py` checks the user's query keywords (e.g., "exercise", "quiz", "answer").
- Based on keywords, it dynamically filters ChromaDB metadata to pull specific content types (theory vs. exercises vs. answer keys).

---

### Conclusion
Sprint 5 transitioned the app from a simple "Prompt -> Response" app into a **Stateful, Agentic Orchestration System**. The architecture is heavily reliant on **LangGraph** for logic flows, **PostgreSQL** for pausing/resuming state, and **ChromaDB** for context retrieval.
