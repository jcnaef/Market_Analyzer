# Resume Tailoring Feature — Implementation Plan

## Context
The Market Analyzer app needs a new AI-powered resume tailoring system. The design document (`design_document.md`) is finalized. This plan breaks the feature into incremental steps where each step produces testable, working functionality before moving to the next. Every step builds on the previous one — no step requires forward references to unbuilt code.

---

## Step 1: Infrastructure — Connection Pool + Migration Runner
**Goal:** Replace per-request DB connections with a pool and add a migration system. Zero new features — this hardens the existing app for everything that follows.

**Files to modify:**
- `src/market_analyzer/db_config.py` — Add `ThreadedConnectionPool`, expose `get_conn()` / `put_conn()` helpers
- `src/market_analyzer/db_queries.py` — Replace all `_get_conn()` / `psycopg2.connect()` calls with pool helpers. Ensure every function uses `try/finally` to return connections.
- `src/market_analyzer/server.py` — Add `@app.on_event("shutdown")` to call `pool.closeall()`
- `run.sh` — Enforce `--workers 1`

**New files:**
- `migrations/001_initial_schema.sql` — Copy of current `data/schema.sql`
- `scripts/run_migrations.py` — Migration runner (~30 lines): creates `migrations` table if needed, reads `migrations/` folder, runs unapplied files in order inside transactions

**How to test:**
- Run existing test suite (`pytest tests/`) — all 86 tests should pass unchanged
- Run `python scripts/run_migrations.py` — should apply 001, re-running should skip it
- Start server, hit existing endpoints (dashboard, jobs, etc.) — verify they still work
- Check that connections are being reused (add a temporary log or check `pool._used` count)

---

## Step 2: Firebase Auth — Backend
**Goal:** Add Firebase initialization, `get_current_user` dependency, users table, and a test endpoint. No frontend changes yet — test with curl/Postman.

**Files to modify:**
- `src/market_analyzer/db_config.py` — Add Firebase Admin SDK initialization (parse private key `\n`, `firebase_admin.initialize_app()`)
- `.env` — Add `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`
- `src/market_analyzer/server.py` — Add `get_current_user` dependency (verify token, get-or-create user row, return `user_id`). Add a test endpoint `GET /api/user/me` [Auth Required] that returns the user row.

**New files:**
- `migrations/002_add_users_table.sql` — Users table with `has_resume` column
- `src/market_analyzer/auth.py` — `get_current_user` dependency, Firebase token verification, user get-or-create query

**How to test:**
- Run migrations — 002 should apply cleanly, re-run skips
- Get a Firebase ID token (use Firebase Auth REST API or a quick test script)
- `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/user/me` — should return user JSON with `has_resume: false`
- Call again — should return same user (get-or-create idempotent)
- Call without token — should return 401
- Existing endpoints still work without auth headers

---

## Step 3: Resume Parser Module
**Goal:** Build the rule-based resume parser as a standalone module. No endpoints yet — tested via unit tests and a CLI script.

**Files to modify:**
- `src/market_analyzer/server.py` — Extract text extraction logic (lines 162-178) into a shared utility function in a new file

**New files:**
- `src/market_analyzer/text_extractor.py` — Shared `extract_text_from_file(tmp_path, ext)` used by both the existing `/api/resume/analyze` and the new parser
- `src/market_analyzer/resume_parser.py` — `parse_resume(raw_text: str) -> dict` returning `ResumeSchema` + `parse_confidence`. Includes:
  - Section detection (keyword matching)
  - Date extraction (regex)
  - Company/title heuristics
  - Bullet point extraction
  - Skills extraction via existing `extract_skills_from_text()`
  - LinkedIn PDF dedicated parser path
- `tests/test_resume_parser.py` — Unit tests with sample resume text strings (LinkedIn format, custom format, minimal/empty)

**How to test:**
- `pytest tests/test_resume_parser.py` — Parser produces expected structure for sample inputs
- Test confidence scores: full resume >= 0.8, partial ~0.4-0.6, garbage text == 0
- Test LinkedIn path detection and parsing
- Run full test suite — existing tests unaffected

---

## Step 4: Resume CRUD Endpoints
**Goal:** Add authenticated endpoints for uploading, saving, and fetching structured resumes. Testable via curl/Postman.

**Files to modify:**
- `src/market_analyzer/server.py` — Add three new endpoints:
  - `POST /api/user/resume/upload` — File upload (5MB limit), calls `text_extractor` + `resume_parser`, returns JSON + confidence
  - `PUT /api/user/resume` — Validates against Pydantic `ResumeSchema` model, upserts to DB, sets `has_resume = true`
  - `GET /api/user/resume` — Fetches resume or 404

**New files:**
- `migrations/003_add_resumes_table.sql` — Resumes table (JSONB `resume_data`, UNIQUE on `user_id`)
- `src/market_analyzer/schemas.py` — Pydantic models: `PersonalInfo`, `ExperienceEntry`, `EducationEntry`, `ResumeSchema`
- `tests/test_resume_endpoints.py` — Integration tests for the three endpoints (auth required, validation, upsert behavior, 5MB limit)

**How to test:**
- Run migrations — 003 applies cleanly
- Upload a real PDF resume with auth token → get back parsed JSON with confidence
- PUT the JSON back (with edits) → 200 success, `has_resume` flips to true
- GET → returns saved JSON
- PUT with malformed JSON → 422 with descriptive error
- Upload > 5MB file → 413/400 rejection
- All existing tests still pass

---

## Step 5: Firebase Auth — Frontend
**Goal:** Add Google sign-in, AuthContext, protected routes. The app should now support login/logout with the avatar UI, and block anonymous users from protected pages.

**Dependencies to install:** `firebase` npm package

**New files:**
- `frontend/src/firebase.js` — Firebase config and initialization
- `frontend/src/context/AuthContext.jsx` — `AuthProvider` with `onAuthStateChanged`, `getIdToken()`, `dbUser` (fetched from `GET /api/user/me`), loading state

**Files to modify:**
- `frontend/src/api.js` — Add axios interceptor that attaches Bearer token from AuthContext. Add `getUserMe()`, `uploadResume()`, `saveResume()`, `getResume()` API functions
- `frontend/src/App.jsx` — Wrap with `AuthProvider`, add route guards for protected pages
- `frontend/src/components/Navbar.jsx` — Add Google avatar / "Sign In" button, profile dropdown with "My Account" and "Logout"

**How to test:**
- Click "Sign In" → Google OAuth popup → successful login → avatar appears in navbar
- Profile dropdown shows "My Account", "Logout"
- Logout → avatar replaced with "Sign In" button
- Navigate to a protected route while logged out → redirected to login
- Refresh page while logged in → auth state persists (Firebase handles this)
- All existing pages still work for anonymous users

---

## Step 6: User Account Page + Resume Upload Flow
**Goal:** Users can upload a resume, review/edit the parsed result, and save it. First-login mandatory upload flow works.

**New files:**
- `frontend/src/pages/AccountPage.jsx` — Upload resume button, editable form (personal info, experience entries, education entries, skills), save button. Displays confidence-based warnings.
- `frontend/src/components/ResumeForm.jsx` — Reusable editable form for `ResumeSchema` (used on both account page and tailoring page)

**Files to modify:**
- `frontend/src/App.jsx` — Add `/account` route (protected, requires auth)
- `frontend/src/context/AuthContext.jsx` — After login, if `dbUser.has_resume === false`, redirect to `/account` with upload prompt message

**How to test:**
- First login → forced to account page with *"Upload your resume to get started"* message
- Upload a PDF → see parsed resume in editable form
- Low confidence → warning banner appears, sections pre-expanded
- Edit fields, click Save → success, `has_resume` becomes true
- Navigate away and back → GET loads saved resume
- Upload a new resume → overwrites previous, shows new parsed data for review
- Upload non-PDF/DOCX → error message
- Upload > 5MB → error message

---

## Step 7: Skill Suggestions Endpoint
**Goal:** Backend endpoint that extracts skills from a job description and returns missing skills. Testable independently before the tailoring UI exists.

**Files to modify:**
- `src/market_analyzer/server.py` — Add `POST /api/suggest-skills` endpoint

**New files:**
- `src/market_analyzer/skill_suggester.py` — Logic: `extract_skills_from_text()` on job description, fuzzy pass with `thefuzz` for 4+ char skills, subtract user's skills, sort by category weight, return top suggestions + highlighted top 3
- `tests/test_skill_suggester.py` — Unit tests with sample job descriptions

**Dependencies to install:** `thefuzz` (backend)

**How to test:**
- POST a job description + current skills → get back suggested missing skills, sorted by weight
- Verify short skills (C, R, Go) only match exactly
- Verify fuzzy matching catches typos (e.g., "Kuberntes")
- Verify `c++`, `.net`, `ci/cd` are found correctly (not destroyed by punctuation stripping)
- Verify Soft_Skills are excluded
- Existing tests pass

---

## Step 8: LLM Tailoring Endpoint + Rate Limiting
**Goal:** The core tailoring endpoint that calls Groq, plus rate limiting. Testable via curl before any frontend tailoring UI exists.

**Files to modify:**
- `src/market_analyzer/server.py` — Add `POST /api/tailor-section` endpoint

**New files:**
- `src/market_analyzer/tailoring.py` — Prompt construction (original bullets + extracted job skills + allowed additions), Groq API call, taxonomy-based guardrail (extract skills from output, compare against allowed), return original + tailored + warnings
- `src/market_analyzer/rate_limiter.py` — Per-user cooldown dict + global rolling window counter. `check_rate_limit(user_id)` returns `(allowed: bool, message: str)`
- `migrations/004_add_tailoring_history.sql` — Tailoring history table
- `tests/test_tailoring.py` — Unit tests for prompt construction, guardrail logic (mock the Groq call), rate limiter

**Dependencies to install:** `groq` (backend)

**How to test:**
- POST original bullets + job description + allowed additions → get back tailored bullets
- Verify only allowed skills appear in output (guardrail works)
- Verify unauthorized skills are flagged in warnings
- Verify skills with punctuation (`c++`, `.net`) pass through guardrail correctly
- Hit endpoint twice within 10 seconds → second request rejected with cooldown message
- Verify tailoring result is saved to `tailoring_history` table
- Run full test suite — rate limiter doesn't interfere with other tests

---

## Step 9: Tailoring Page + Job Board Integration
**Goal:** The frontend tailoring experience — from clicking "Tailor Resume" on a job listing through to reviewing and approving diffs.

**Dependencies to install:** `diff-match-patch` (frontend)

**New files:**
- `frontend/src/pages/TailoringPage.jsx` — Load user's resume, display experience blocks with "Tailor to Job" buttons, tailor modal (job description pre-filled, allowed additions input, skill suggestions), diff review with approve/reject
- `frontend/src/components/DiffView.jsx` — Side-by-side diff using `diff-match-patch`, character-level red/green highlighting
- `frontend/src/components/SkillSuggestions.jsx` — Calls `/api/suggest-skills`, displays clickable skill chips that append to allowed additions
- `frontend/src/components/TailorModal.jsx` — Modal with job description, allowed additions, skill suggestions, submit button

**Files to modify:**
- `frontend/src/App.jsx` — Add `/tailor` route (protected, requires auth + has_resume)
- `frontend/src/pages/JobBoard.jsx` — Add "Tailor Resume" button to each listing. If not logged in, save job to `sessionStorage` keyed by job ID, redirect to login with params. If logged in, navigate to `/tailor?jobId=X`
- `frontend/src/api.js` — Add `suggestSkills()`, `tailorSection()` API functions

**How to test:**
- Click "Tailor Resume" on a job while logged in → navigate to tailoring page with job description pre-filled
- Click "Tailor Resume" while logged out → login flow → upload flow (if first time) → tailoring page with job description preserved from `sessionStorage`
- Click "Tailor to Job" on an experience block → modal opens with skill suggestions
- Click skill suggestions → added to allowed additions
- Submit → loading state → diff view appears with character-level highlighting
- Approve → bullets updated in the resume form
- Reject → original bullets preserved
- Rate limit hit → user-friendly message displayed

---

## Step 10: PDF Export
**Goal:** Users can download their resume as an ATS-friendly PDF.

**Dependencies to install:** `@react-pdf/renderer` (frontend)

**New files:**
- `frontend/src/components/ResumeTemplate.jsx` — `@react-pdf/renderer` document component that maps `ResumeSchema` to a clean ATS-friendly PDF layout
- `frontend/src/components/PDFDownloadButton.jsx` — Button that triggers deferred PDF generation with loading spinner

**Files to modify:**
- `frontend/src/pages/AccountPage.jsx` — Add "Download PDF" button
- `frontend/src/pages/TailoringPage.jsx` — Add "Download PDF" button (after approving tailored changes)

**How to test:**
- Click "Download PDF" on account page → PDF downloads with correct resume content
- Click "Download PDF" after tailoring → PDF reflects the tailored bullets
- Verify PDF renders all sections (personal info, experience, education, skills)
- Verify loading spinner shows during generation
- Open PDF in an ATS parser (or just verify clean text extraction) to confirm ATS-friendliness
