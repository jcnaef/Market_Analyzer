# Architecture Design Document: AI-Powered Resume Tailoring System

## 1. System Overview
This feature allows users to tailor specific sections of their parsed resume to a target job description using the Groq API (Llama 3 8B). To prevent hallucinations and formatting degradation, the system uses a **Data-Driven Architecture**: the resume is stored and manipulated as structured JSON in PostgreSQL, specific data blocks are sent to the AI for modification alongside strictly controlled variable inputs, and the final result is rendered into predefined ATS-friendly PDF templates on the frontend.

## 2. Authentication & User Management

### Google OAuth via Firebase Auth (Free Tier)
* **Login UI:** Google profile icon/avatar in the top-right corner of the navigation bar.
  * Logged out: Displays a "Sign In" button.
  * Logged in: Displays the user's Google avatar with a dropdown menu containing "My Account" and "Logout".
* **Access Control:**
  * Anonymous users can access all features **except** Resume Analyzer and Resume Tailoring.
* **First Login Flow & State Preservation:**
  * After first sign-in, the user is **required** to upload their resume before proceeding. Message: *"Upload your resume to get started — you need it to tailor your resume to job listings."*
  * **State Preservation:** If an anonymous user clicks "Tailor Resume" on a job board, the frontend stores the job description in `sessionStorage` keyed by job ID (e.g., `tailor_pending_${jobId}`) and appends a redirect parameter to the URL (e.g., `/login?redirectTo=/tailor&jobId=123`). After the user completes the mandatory upload and saves their resume, the app reads the specific `sessionStorage` key from the redirect parameter and routes them to the Tailoring Page with the job description pre-filled. The key is deleted after loading to prevent stale data. Using `sessionStorage` instead of `localStorage` ensures automatic cleanup when the tab closes and supports multiple pending job descriptions without overwriting.
* **Auth Middleware (Backend):**
  * Only user resume and tailoring API endpoints require authentication. All other endpoints (including the existing anonymous `/api/resume/analyze`) remain publicly accessible.
  * **Local JWT Verification:** Use `firebase_admin.auth.verify_id_token()` which verifies tokens locally using cached Google public keys (auto-refreshed every ~6 hours). This avoids a network call to Firebase on every authenticated request.
  * **Firebase Initialization:** Store Firebase service account credentials as environment variables. The private key must be parsed before passing to Firebase — environment variables encode `\n` as literal two-character strings, so replace `\\n` with actual newlines when loading (e.g., `os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n")`). Initialize `firebase_admin` once at startup in `db_config.py`.
  * **FastAPI Dependency:** Implement auth as a reusable `Depends(get_current_user)` dependency applied only to protected endpoints, not as global middleware.

### Database: Users Table
* `id`: Primary key (SERIAL)
* `firebase_uid`: String (unique, from Firebase)
* `email`: String
* `display_name`: String
* `avatar_url`: String (Google profile photo)
* `has_resume`: Boolean (default false — used by frontend to enforce the mandatory upload flow)
* `created_at`: Timestamp
* `updated_at`: Timestamp

### User Creation (Get-or-Create)
The `get_current_user` FastAPI dependency verifies the Firebase token and then performs a get-or-create against the `users` table using the `firebase_uid`. On first login, the user row is inserted with profile info from the Firebase token (`email`, `display_name`, `avatar_url`). On subsequent logins, `display_name` and `avatar_url` are updated in case the user changed their Google profile. The dependency returns the internal `user_id` (not the Firebase UID) for use in downstream queries.

## 3. Core Data Structures (Source of Truth)
The application state revolves around a standardized JSON schema. The LLM only ever interacts with isolated blocks of this data.

### Separation from Existing Resume Analyzer
The existing `/api/resume/analyze` endpoint remains unchanged — it extracts skills from an uploaded file and returns market demand analysis for anonymous users via `sessionStorage`. The new tailoring system uses a **separate set of authenticated endpoints** (`/api/user/resume/*`) that store structured resume JSON in PostgreSQL. The two systems share the underlying text extraction utility (pdfplumber/python-docx) but serve different purposes and different user flows.

**`ResumeSchema` (JSON) — stored in PostgreSQL per user (one resume per user, overwritten on re-upload):**
* `personal_info`: Object (Name, email, links)
* `summary`: String
* `experience`: Array of Objects `[{ id, company, title, dates, bullet_points: [strings] }]`
* `education`: Array of Objects `[{ id, institution, degree, dates, details: [strings] }]`
* `skills`: Array of Strings
* `raw_text`: String (original extracted text, always preserved)

### Database: Resumes Table
* `id`: Primary key (SERIAL)
* `user_id`: Integer, Foreign key → users(id), UNIQUE (one resume per user), ON DELETE CASCADE
* `resume_data`: JSONB (the `ResumeSchema` object above)
* `raw_text`: Text (original extracted text, kept as a top-level column for easy access)
* `created_at`: Timestamp
* `updated_at`: Timestamp

The `resume_data` JSONB column stores the full `ResumeSchema`. Using JSONB over a flat relational model keeps the schema flexible and avoids excessive joins when reading/writing the full resume. The `user_id` UNIQUE constraint enforces the one-resume-per-user rule — upserts use `ON CONFLICT (user_id) DO UPDATE`.

### Tailoring History
Each tailoring result is persisted to preserve past work. Stored in a `tailoring_history` table:
* `id`: Primary key (SERIAL)
* `user_id`: Foreign key → users(id), ON DELETE CASCADE
* `experience_company`: String (company name from the experience block, for display context)
* `experience_title`: String (job title from the experience block)
* `job_title`: String (from the target job listing, for display)
* `original_bullets`: Text array
* `tailored_bullets`: Text array
* `created_at`: Timestamp

The `experience_company` and `experience_title` fields identify which resume section was tailored, so users can map history entries back to specific experience blocks when revisiting past results.

## 4. Resume Parsing (Rule-Based Approach)
The resume parser converts uploaded PDF/DOCX files into the `ResumeSchema` JSON format. It uses rule-based logic and regex patterns to avoid LLM API costs and heavy NLP dependencies.

### Parsing Strategy
1. **Text Extraction:** Use `pdfplumber` (PDF) and `python-docx` (DOCX) to extract raw text. This logic is shared with the existing `/api/resume/analyze` endpoint via a common utility function.
2. **Section Detection:** Identify section headings via keyword matching against common labels ("Experience", "Education", "Skills", etc.).
3. **Date Extraction:** Use regex patterns for common resume date formats (`Jan 2023 - Present`, `2021-2023`, `MM/YYYY`, etc.). Resume dates are highly predictable and do not require NLP.
4. **Company/Title Extraction:** Within detected "Experience" sections, treat the first non-date line after a heading as the company/title. Use line positioning and formatting heuristics (bold text in DOCX, uppercase patterns in PDF).
5. **Bullet Point Extraction:** Lines starting with `•`, `-`, `*`, or indented text under a job/education entry.
6. **Skills Extraction:** Existing `skills.json` matching applied to detected "Skills" section.

### Parse Confidence Score
The parser returns a `parse_confidence` score (0.0–1.0) based on how many of the 5 major sections (personal_info, summary, experience, education, skills) were successfully identified. The frontend uses this to adjust the UI:
* **confidence >= 0.4:** Show the editable pre-filled form normally.
* **confidence < 0.4:** Show a warning banner: *"We had trouble parsing your resume. Please review and fill in the missing sections."* Pre-expand all form sections so the user can see what's empty.
* **confidence == 0:** Show an empty form with message: *"We couldn't parse this file. Please enter your information manually, or try uploading a LinkedIn PDF export."*

### The "Golden Path" Fallback
* Resumes are highly non-standard. The upload UI will prominently feature a "Golden Path" recommendation: *"For best results, upload your LinkedIn Profile as a PDF."*
* The backend will include a highly accurate, dedicated parser specifically for the predictable DOM/PDF structure of LinkedIn exports, falling back to the heuristic parser for custom layouts.
* **User Review Step:** After parsing, the user is presented with an **editable pre-filled form** showing the parsed resume data to correct any errors before saving.

## 5. Frontend Architecture (React)

### Auth State Management
* **`AuthContext` Provider:** Wraps the app and listens to `firebase.auth().onAuthStateChanged()`. Exposes `user` (Firebase user object or null), `loading` (boolean, true while Firebase initializes), and `dbUser` (the user row from the backend, including `has_resume`).
* **Token Handling:** All authenticated API calls use `user.getIdToken(true)` to get a fresh token. Firebase auto-refreshes tokens before they expire (1-hour lifetime), so `getIdToken()` always returns a valid token without manual refresh logic. Attach the token via an axios request interceptor as `Authorization: Bearer <token>`.
* **Route Guards:** Protected routes (tailoring page, account page) check `AuthContext`. If `user` is null and `loading` is false, redirect to login. If `user` exists but `dbUser.has_resume` is false, redirect to the mandatory upload flow.

### Navigation & Auth UI
* Google avatar/sign-in button in the top-right corner of the nav bar.
* Profile dropdown: "My Account", "Logout".

### User Account Page
* Accessible via the profile dropdown (not a public nav link).
* **Features:** Upload a new resume (triggers re-parsing and editable review form) and edit current parsed data.

### The Tailoring Page
* **Not a selectable nav tab** — only reachable via the "Tailor Resume" button on job board listings or via the `sessionStorage` post-login redirect hook.
* **Tailoring UI:**
  * Users view their resume in a form-based editor.
  * Each `experience` block has a "Tailor to Job" button.
  * Clicking opens a Modal requiring:
    1. `job_description` (pre-filled).
    2. `allowed_additions` (text input for hard skills the user explicitly permits).
  * The Modal dynamically displays **Skill Suggestions** that the user can click to append to `allowed_additions`.
* **Diff Review:**
  * Side-by-side view using Google's `diff-match-patch` for character-level red/green highlighting within each bullet. This produces granular inline diffs (e.g., highlighting just "React" inserted mid-sentence) rather than flagging the entire line as changed.
  * Original text on the left, tailored text on the right. User must explicitly approve changes.

### PDF Rendering Engine
* Use `@react-pdf/renderer` to map the `ResumeSchema` JSON state directly into visual PDF templates client-side.
* **Deferred Rendering:** Do not pre-render the PDF during editing. The resume is displayed and edited as a normal React form. PDF generation only occurs when the user clicks "Download PDF," avoiding perceived slowness during the editing workflow.
* Ensure fonts are loaded asynchronously and provide a loading spinner during PDF generation.

## 6. Backend Architecture (FastAPI)

### Database Connection Pool
The current codebase opens a new `psycopg2.connect()` for every request via `_get_conn()` in `db_queries.py`. With a single worker, this serialized connection overhead (TCP handshake, auth, teardown per query) becomes a bottleneck. Replace with a connection pool initialized once at startup:

* Use `psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)` in `db_config.py`. `ThreadedConnectionPool` is safe for FastAPI's sync endpoints which run in a thread pool executor.
* Expose `get_conn()` and `put_conn(conn)` helpers that call `pool.getconn()` and `pool.putconn()`. All query functions in `db_queries.py` use these instead of opening new connections.
* On `@app.on_event("shutdown")`, call `pool.closeall()` to cleanly release connections.
* Using a pool means connections are reused across requests — a query that previously took ~5-10ms of connection overhead now takes <1ms to acquire a pre-established connection.

### Global State (Startup Initialization)
* Load a local `skills.json` file into memory on server startup.
* Format: `{"Languages": [], "Frameworks_Libs": [], "Tools_Infrastructure": [], "Concepts": [], "Soft_Skills": []}`
* Store the `Soft_Skills` array as a lowercase Python `Set` for O(1) lookups.
* Build a **canonical skill lookup map** at startup: `{skill.lower().strip(): skill for category in taxonomy.values() for skill in category}`. This preserves the original casing and punctuation of skills like `c++`, `.net`, `node.js`, and `ci/cd` while allowing case-insensitive lookups.

### User Resume Endpoints (Authenticated)
These endpoints are separate from the existing anonymous `/api/resume/analyze` and use the `Depends(get_current_user)` auth dependency.

* **`POST /api/user/resume/upload`** [Auth Required] — Accepts PDF/DOCX (max 5MB, enforced by reading content length before processing), extracts text (shared utility with `/api/resume/analyze`), runs the structured parser, returns `ResumeSchema` JSON with `parse_confidence` for the editable review form. Does **not** save to database — the user must review and confirm first.
* **`PUT /api/user/resume`** [Auth Required] — Validates the payload against a Pydantic `ResumeSchema` model (enforces required fields, correct types, array structures) and saves to the database (upsert via `ON CONFLICT (user_id) DO UPDATE`). Sets `users.has_resume = true`. Rejects payloads that fail validation with a 422 and descriptive error.
* **`GET /api/user/resume`** [Auth Required] — Fetches the user's saved resume JSON. Returns 404 if no resume exists (frontend uses this to enforce the upload-first flow).

### Endpoint: Suggest Skills (`POST /api/suggest-skills`) [Auth Required]
* **Payload In:** `{"job_description": string, "current_resume_skills": string[]}`
* **Logic:**
  1. Extract skills from the `job_description` using `extract_skills_from_text()` — the same function used throughout the app. This avoids the need to strip punctuation before tokenizing (which would destroy skills like `c++`, `.net`, `ci/cd`).
  2. **Fuzzy Matching Pass:** After the initial exact extraction, run a secondary fuzzy pass (Levenshtein distance via `thefuzz`) over the raw job description text for skills 4+ characters long to catch typos/variations (e.g., "Kuberntes" → "kubernetes"). For skills 1-3 characters long (e.g., C, R, Go), require exact case-sensitive regex match (`\bC\b`) — do *not* fuzzy match these.
  3. Calculate missing skills: Subtract `current_resume_skills` from the extracted job skills.
  4. Sort missing skills based on categorical weight: `Languages (5) > Frameworks_Libs (4) > Tools_Infrastructure (3) > Concepts (2)`. Exclude `Soft_Skills`.
* **Payload Out:** `{"suggested_skills": [...], "highlighted_top_3": ["Skill_1", "Skill_2", "Skill_3"]}`

### Endpoint: Tailor Section (`POST /api/tailor-section`) [Auth Required]
* **Payload In:** `{"original_text": ["bullet 1"], "job_description": "...", "allowed_additions": ["React"]}`
* **Logic:**
  1. **Pre-process job description:** Instead of sending the full job description to the LLM (which can be 500–2000 tokens), extract skills from it using `extract_skills_from_text()` and send only the extracted skill list. This significantly reduces token usage per request, helping stay within Groq's tokens-per-minute limit.
  2. Construct a prompt with the original bullets, extracted job skills, and allowed additions. **Prompt Engineering:** Include strict system instructions:
      * *"You may only add the following skills. You must spell and capitalize them EXACTLY as they appear in this list: {allowed_additions}."*
      * *"Do not include ANY proper nouns, technologies, or capitalized concepts unless they are present in the original text or the allowed additions list."*
  3. Send to **Groq API** (Llama 3 8B).
  4. **Taxonomy-Based Guardrail:** Instead of stripping punctuation (which destroys skills like `c++`, `.net`, `ci/cd`), use the existing `extract_skills_from_text()` function from `cleaner.py` to identify skills in both the original text and the LLM output. Compute `new_skills = output_skills - original_skills`. Any skill in `new_skills` that is not in `allowed_additions` (compared via lowercase match) is flagged as an unauthorized addition warning.
  5. Return original and tailored text for diff display.
* **Payload Out:** `{"original_bullets": [...], "tailored_bullets": [...], "warnings": [...]}`

### Rate Limiting (Groq Free Tier)
Groq's free tier has strict rate limits (~30 req/min for Llama 3 8B). To prevent one user from exhausting the shared API key:
* **Per-user cooldown:** Maintain an in-memory `dict[user_id, datetime]` of last tailoring request timestamps. Reject requests if the user's last request was within the last 10 seconds with a user-friendly message: *"Please wait a few seconds before tailoring again."*
* **Global rate tracking:** Maintain a rolling count of requests in the current 60-second window. If the global limit is approaching, reject with: *"High demand — please try again in 30 seconds."*
* **Single Worker Constraint:** Because rate limiting state is stored in-memory, the server **must run with a single uvicorn worker** (`--workers 1`). Multiple workers would each have their own memory space, so worker 1's cooldown dict would be invisible to worker 2, effectively bypassing the rate limiter. Document this in `run.sh` and enforce it in the startup command.

## 7. Job Board Integration
* Each job listing displays two buttons: "Apply" (external link) and "Tailor Resume".
* If the user is not logged in, clicking "Tailor Resume" saves the job text to `sessionStorage` (keyed by job ID), appends redirect parameters, and initiates the login/upload flow to prevent state loss.

## 8. Database Migrations
Schema changes are managed via numbered SQL files in a `migrations/` directory:

```
migrations/
  001_initial_schema.sql
  002_add_users_table.sql
  003_add_resumes_table.sql
  004_add_tailoring_history.sql
```

A `migrations` table tracks which files have been applied:
```sql
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    filename TEXT UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

A small Python runner script reads the `migrations/` folder, skips already-applied files, and executes new ones in order. **Each migration file is executed inside a transaction** — the runner wraps the SQL execution and the `INSERT INTO migrations` record in a single `BEGIN`/`COMMIT` block. If the SQL fails at any point, the entire transaction is rolled back, leaving both the schema and the migrations table unchanged. This ensures the database is never left in a half-migrated state after a crash or syntax error. This avoids the complexity of Alembic while providing safe, versioned, repeatable schema changes.

## 9. Dependencies

### Backend (add to pyproject.toml)
* `firebase-admin` — Token verification and user management
* `groq` — Groq API client for Llama 3 8B
* `thefuzz` — Lightweight fuzzy string matching (Levenshtein distance) for skill suggestions

**Note:** spaCy was considered for NER during resume parsing but excluded. Resume dates are predictable enough for regex, and the editable review form serves as a safety net for parsing errors. Dropping spaCy avoids ~50MB+ of model downloads and deployment complexity.

### Frontend (add to package.json)
* `firebase` — Firebase Auth client SDK
* `@react-pdf/renderer` — Client-side PDF generation
* `diff-match-patch` — Google's diff library for computing character-level diffs in the tailoring review. Produces more granular, human-readable diffs than line-level alternatives — ideal for comparing bullet points where only a few words change.
