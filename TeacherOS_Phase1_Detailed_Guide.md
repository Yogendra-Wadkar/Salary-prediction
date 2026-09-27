# TeacherOS Phase 1 — Detailed Deep Dive

This document is specifically tailored for studying **Phase 1** of the TeacherOS project. It breaks down the foundational aspects of the application, including the frontend stack, FastAPI mechanisms, Authentication (JWT), and a deep dive into the Database Architecture using SQLAlchemy.

---

## 1. The Technology Stack

### Frontend: HTML, CSS, and Vanilla JavaScript
For Phase 1, we intentionally avoided heavy frameworks (like React, Angular, or Vue). The frontend is a **pure Vanilla stack**:
*   **HTML (HyperText Markup Language):** Provides the skeleton and structure of the pages (e.g., `index.html`, `dashboard.html`). It defines where inputs, buttons, and text belong.
*   **CSS (Cascading Style Sheets):** Controls the visual aesthetics (colors, fonts, layout, spacing).
*   **Vanilla JavaScript (JS):** Handles the logic on the browser side without external libraries. We use JavaScript's built-in `fetch()` API to make HTTP requests (GET, POST) to our FastAPI backend. 
    *   *How it connects:* When a user clicks "Login", JavaScript captures the username and password from the HTML form, sends a `POST` request to the backend, waits for the response, and then redirects the user to the dashboard if successful.

### Backend: FastAPI
**FastAPI** is a modern, fast web framework for building APIs with Python. 
*   **Why we use it:** It is incredibly fast, automatically validates data using **Pydantic** (via `schemas.py`), and auto-generates documentation (Swagger UI).
*   **Routers:** In FastAPI, we use `APIRouter` to split our application into smaller, manageable files. Instead of having 50 APIs in `main.py`, we group them logically. For example, `backend/routers/auth.py` handles user login/registration, and `backend/routers/curriculum.py` handles curriculum data.

---

## 2. Authentication & Authorization (Login / Logout)

We use **JWT (JSON Web Tokens)** for authentication. The logic resides in `backend/auth.py` and `backend/routers/auth.py`.

### How JWT Works in TeacherOS:
1.  **Registration (`/auth/register`):** 
    *   The user sends a username, email, and plain text password.
    *   FastAPI uses the `pwdlib` library (Argon2 algorithm) to hash the password. **We never save plain text passwords in the database.** We save the hashed string.
2.  **Login (`/auth/login`):** 
    *   The user sends their username and password.
    *   The backend retrieves the user from the database and uses `pwdlib.verify` to check if the entered password matches the hash.
    *   If valid, FastAPI generates a **JWT (JSON Web Token)**. This token is a digitally signed string (signed using a `SECRET_KEY` from our `.env` file) that contains the user's ID (`sub`).
    *   The token is sent back to the frontend.
3.  **Authorization (Protecting Routes):**
    *   The frontend saves this token in `localStorage` or `sessionStorage`.
    *   For every subsequent request (e.g., fetching curricula), the frontend JavaScript attaches this token to the HTTP Headers: `Authorization: Bearer <token>`.
    *   FastAPI uses a dependency called `get_current_user` to intercept the request, decode the token, verify the signature, extract the User ID, and fetch the user from the database. If the token is invalid or expired, the request is rejected with a 401 Unauthorized error.
4.  **Logout:**
    *   Because JWTs are *stateless* (the backend doesn't store active sessions), logging out is handled entirely on the **frontend**. 
    *   When the user clicks "Logout", the Vanilla JavaScript simply deletes the token from `localStorage` and redirects the user to the login page. Without the token, the user can no longer access protected APIs.

---

## 3. Database Architecture (SQLAlchemy & Relationships)

### What is SQLAlchemy?
**SQLAlchemy** is an **ORM (Object-Relational Mapper)**. 
*   **Role in Phase 1:** Instead of writing raw SQL strings like `SELECT * FROM users WHERE id=1;`, SQLAlchemy allows us to interact with the database using Python objects and classes. It translates our Python code into SQL queries automatically. 
*   It provides built-in protections against SQL injection attacks.

### The Tables and Relationships
In Phase 1, our database consists of **three primary tables**, defined in `backend/models.py`.

#### 1. The `users` Table
*   **Columns:** `id` (Primary Key), `username`, `email`, `hashed_password`, `is_active`.
*   **Purpose:** Stores user credentials and profile information.

#### 2. The `curriculums` Table
*   **Columns:** `id` (Primary Key), `user_id` (Foreign Key), `teacher_name`, `subject`, `grade`, `academic_year`, `start_month`, etc.
*   **Purpose:** Stores the high-level metadata for a specific curriculum.

#### 3. The `curriculum_weeks` Table
*   **Columns:** `id` (Primary Key), `curriculum_id` (Foreign Key), `order_index`, `month`, `week`, `topic`, `planned_content`, `status`, etc.
*   **Purpose:** Stores the granular, week-by-week lesson plan details for a specific curriculum.

### Relationship Mapping (How they are connected)

We use **One-to-Many** relationships across the board.

1.  **User to Curriculums (1 : N)**
    *   *Relationship:* One User can create Many Curriculums.
    *   *Database Level:* The `curriculums` table has a Foreign Key column called `user_id` that points to `users.id`. 
    *   *SQLAlchemy Level:* 
        *   In `User`: `curriculums = relationship("Curriculum", back_populates="user")`
        *   In `Curriculum`: `user = relationship("User", back_populates="curriculums")`
    *   *Security Filter:* Whenever an API fetches a curriculum, we *always* filter by the logged-in user to ensure privacy: 
        `db.query(Curriculum).filter(Curriculum.user_id == current_user.id).all()`

2.  **Curriculum to Curriculum Weeks (1 : N)**
    *   *Relationship:* One Curriculum contains Many Weeks.
    *   *Database Level:* The `curriculum_weeks` table has a Foreign Key column called `curriculum_id` that points to `curriculums.id`.
    *   *SQLAlchemy Level:* 
        *   In `Curriculum`: `weeks = relationship("CurriculumWeek", back_populates="curriculum", cascade="all, delete-orphan")`
        *   In `CurriculumWeek`: `curriculum = relationship("Curriculum", back_populates="weeks")`
    *   *Cascade Delete:* Notice the `cascade="all, delete-orphan"`. This is a crucial detail. It means if a user deletes a `Curriculum`, SQLAlchemy will automatically delete all the associated `CurriculumWeek` rows so we don't have orphaned data floating in the database.

### Filtering Data in Phase 1
When querying data, we heavily rely on SQLAlchemy's `.filter()` method. 
For example, in the dashboard API (`backend/routers/dashboard.py`):
```python
weeks = db.query(CurriculumWeek).filter(CurriculumWeek.curriculum_id == curriculum_id).all()
```
Here, SQLAlchemy translates the `.filter()` method into a `WHERE` clause in SQL, fetching only the rows in the `curriculum_weeks` table where the `curriculum_id` matches the curriculum we are viewing.
