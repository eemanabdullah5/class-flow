# ClassFlow: project context for Claude

**Student Assignment and Progress Tracker**, a beginner's academic mini project inspired by Google Classroom (not a clone).
The owner is a **beginner**. Work **step by step**: explain the *why* in plain language, describe each step and **wait for approval
before implementing it**, keep changes small, and end every step with what was built, how to test it, and a commit command.
Avoid unnecessary libraries. Match the existing code style and comment density.

## Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.x ORM (2.0 `Mapped` style), SQLite, pytest. Tables are created with `create_all()` (no Alembic).
- **Frontend:** React 19 (JavaScript, **not** TypeScript), Vite, `react-router` **v7** (not v8), Vitest + React Testing Library. Plain CSS (`src/styles.css` with CSS variables), no UI library, no Axios.
- Dev proxy: Vite forwards `/api` → `http://localhost:8000`, so no CORS setup.

## Progress (as of 2026-10-26)

| Phase | Status |
|---|---|
| 0 Setup · 1 Database · 2 Auth · 3 Courses · 4 Assignments · 5 Submissions + grading | ✅ done |
| 6 Frontend (6.1 login · 6.2 routing · 6.3 student pages · 6.4 teacher pages · 6.5 polish) | ✅ done |
| 7 Grade undo (stack): 7.1 table · 7.2 `Stack` · 7.3 record changes · 7.4 endpoints · 7.5 undo button | ✅ done |
| 8 Topic tree, prerequisites, cycle detection: 8.1 topic tree API · 8.2 prerequisite graph + cycles · 8.3 Topics page | ✅ done |
| 9 Weighted scores · letter grades + stats · 3 SQL reports, plus Results page and "My result" card | ✅ done (**letter scale and the 3 reports are Claude's defaults: user to confirm against their brief**) |
| **10 Full workflow test, README, security doc, ER diagram update, demo plan** | ⏭️ **NEXT: first remind the user to do the manual testing in `docs/manual-testing.md`** |

Tests at last count: **backend 379 passed**, **frontend 102 passed**. The full teacher → student workflow works end to end.

**Manual testing is deferred.** The user wants to do all hands-on testing once the app is complete. After each phase, **append its
checks to `docs/manual-testing.md`** (next free section) instead of asking them to test now. Remind them before Phase 10.

## Phase 7: grade undo (done; the decisions behind it)

- New `GradeChange` model/table (`grade_changes`): submission/assignment + student, `teacher_id`, `old_score` (nullable = "no grade"),
  `old_feedback`, `new_score`, `changed_at`, `undone` flag.
- `app/services/grading.py::set_grade()` is the only place teachers' grade changes happen, so it records the old value there
  (skipped when score and feedback are unchanged). `undo_last_change()` restores grades directly, never via `set_grade()`, so undo isn't recorded (no redo).
- A pure, separately tested stack logic piece (push/pop/peek, LIFO).
- `POST /api/grades/undo` (pop the teacher's latest not-undone change and restore the old value; old "no grade" deletes the grade,
  which unlocks the submission) and `GET /api/grades/undo` (preview what undo would do). **One transaction.**
- Each teacher has **one** stack across all their assignments (not per assignment); a teacher can never undo another's change;
  students get 403. Repeated undo, **no redo**. Empty stack: preview `null`, undo 409.
- Frontend: `UndoGradeButton` on the teacher's assignment page with a preview (e.g. "Sara Ahmed: 18 → no grade"; names the
  assignment if it's another one), disabled when empty. `GradeRow` syncs its form when the saved grade's values change.
- Tests: LIFO order, repeated undo, empty stack, first grade undo deletes the grade and unlocks, cross-teacher isolation, student 403, UI button.

## Agreed decisions (don't change without asking)

- **Roles:** public register **always creates a student**. Teachers only via `python -m app.seed` (demo) or `python -m app.create_teacher`.
- **Auth:** bcrypt hashes; JWT HS256, 60 min, secret from `JWT_SECRET` in `backend/.env` (min 32 chars, placeholders rejected);
  token in **sessionStorage**; no refresh tokens; logout clears the token (a JWT stays valid until expiry; document this).
  `get_current_user` reloads the user from the DB each request.
- **Permissions:** outsiders get **404** (not 403) for courses/assignments/submissions they aren't part of; wrong role gets 403.
  Shared checks live in `app/access.py`. Student endpoints never take a student id (always from the token).
- **Courses:** join by 6-char code (no 0/O/1/I); one teacher per course.
- **Assignments:** category quiz 10 / assignment 10 / midterm 30 / project 50, **fixed** weights (`app/scoring.py`, mirrored in
  `frontend/src/utils/categories.js`). Midterm is in class: upload/turn-in → 409, can be graded any time, and work with uploads
  can't be switched to midterm (409). All times are UTC (`UTCDateTime` column type); the API requires timezone-aware datetimes.
- **Submissions:** one file per submission; upload (draft) → "mark as done" (submitted) → unsubmit allowed until graded; late allowed and
  flagged (`is_late` computed). Files: PDF/DOCX/ZIP/PNG/JPG, ≤10 MB, extension **and** magic bytes checked, random stored names in
  `backend/uploads/` (git-ignored), download only via a permission-checked endpoint with `Content-Disposition: attachment` + `nosniff`.
- **Grading:** separate `grades` table; score 0..max_points; missing work can be given 0; drafts can't be graded **before** the due date
  (allowed after); grading locks the submission (no resubmit). Combine items by **points** (sum scores / sum max points).
- **Grades shown:** absolute grading, **pass = 50%**; letters A 80+ · B 70+ · C 60+ · D 50+ · F below 50 (`LETTER_SCALE` in
  `app/scoring.py`; a default, not yet confirmed by the user). Percent rounded to 1 decimal first; letter/pass use the rounded value.
- **Missing work counts as 0** after the deadline (no submission, or only a draft). Handed in but ungraded → not counted yet;
  ungraded midterm → not counted. A category with nothing counted is left out and the other weights scale up.
- **Results:** `GET /api/courses/{id}/my-result` (student), `GET /api/courses/{id}/results` (teacher: each student + stats from
  `app/stats.py`: count, mean, min, max, population variance, pass proportion, over students who have a result). Not stored.
- **Topic tree:** `topics.parent_id` (null = top level), same course only; moving a topic inside itself/its subtopics → 409;
  deleting a topic deletes its subtopics (cascade); siblings in the order added. Pure helpers in `app/tree.py`.
  Teacher-only writes (`POST /api/courses/{id}/topics`, `PATCH`/`DELETE /api/topics/{id}`); members read the tree.
- **Topic prerequisites:** `topic_prerequisites` (topic_id needs prerequisite_id first), same course only; self → 422,
  duplicate → 409, loop → 409 with the chain ('That would make a loop: "A" needs "B" needs "A".'). The tree includes
  `prerequisite_ids`; `GET /api/courses/{id}/topics/study-order` gives a topological order (ties = order added).
  Generic `app/graph.py` (find_path, would_create_cycle, find_cycle, dependency_order).
- **Topics page:** `/courses/:id/topics` (linked from the course page), shared; teacher edits inline (`TopicTree` → `TopicEditor`),
  dropdowns hide impossible moves but loops are left to the backend so its message is shown; delete asks `window.confirm`.
- **Topic prerequisites** between topics within one course (generic `graph.py` so it can be reused); **course prerequisites deferred** (later).
- The 3 reports are **raw SQL** via `text()` in `app/routers/reports.py` (teacher only, `/api/courses/{id}/reports/...`):
  `assignments` (per assignment: turned in, late, missing, graded, avg/min/max), `students` (per student: turned in, late, graded,
  raw points of graded work), `missing-late` (past-due missing or late work). Chosen by Claude; **confirm with the user's brief**.
- **Databases made before Phase 9** still have the old category CHECK (`create_all()` doesn't alter tables): delete `classflow.db`
  and re-seed (noted in `docs/manual-testing.md` setup).

## Run it (Windows, first time on a new machine)

The repo doesn't contain `.env`, the database, or uploads. Each machine creates its own.

```powershell
git clone https://github.com/eemanabdullah5/class-flow.git
cd class-flow

# Backend (needs Python 3.12+ from python.org, with "Add python.exe to PATH" ticked)
cd backend
py -m venv .venv
.venv\Scripts\activate            # if PowerShell blocks it: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
#   -> paste the output as JWT_SECRET=... in backend\.env, and set DEMO_PASSWORD=something-8-plus
python -m pytest -q               # expect 379 passed
python -m app.seed                # demo accounts + sample course
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Frontend (second terminal; needs Node.js LTS from nodejs.org)
cd class-flow\frontend
npm install
npm test                          # expect 102 passed
npm run dev                       # http://localhost:5173
```

On macOS/Linux use `python3 -m venv .venv` and `source .venv/bin/activate` instead.

**Demo accounts** (password = `DEMO_PASSWORD`): `teacher@example.com`, `student1@example.com` (enrolled), `student2@example.com` (not enrolled).

## Where things are

- `backend/app/`: `main.py`, `config.py`, `database.py`, `models.py`, `schemas.py`, `security.py`, `deps.py` (auth guards),
  `access.py` (permission checks), `routers/` (auth, courses, assignments, submissions, grades, topics, results, reports), `services/` (courses, files, grading + undo, results), `stack.py`, `tree.py`, `graph.py`, `scoring.py`, `stats.py`,
  `seed.py`, `create_teacher.py`
- `backend/tests/`: `conftest.py` has the shared fixtures: `session`, `client`, `make_user`, `auth_header()`, `classroom`, and a temp upload dir
- `frontend/src/`: `api/client.js` (the only place that calls fetch), `auth/` (AuthContext, ProtectedRoute), `hooks/` (useApi,
  useDocumentTitle), `components/`, `pages/`, `utils/`, `__tests__/` (`helpers.jsx` has `fakeBackend` + `renderApp`)
- `docs/`: `er-diagram.md` (Mermaid; update it when adding tables), `manual-testing.md` (deferred checklist)
- `README.md` currently has the folder structure only; the full README is written in Phase 10.

## Conventions

- Run backend commands from `backend/` with the venv active; frontend commands from `frontend/`.
- Every new endpoint gets permission tests (wrong role, outsider, no token) as well as happy-path tests.
- Never log or print passwords, tokens or secrets. Never commit `.env`, `*.db`, `uploads/` or `node_modules/`.
- Commit messages end with the attribution line from the system reminder, when present. The user usually commits and pushes themselves.
