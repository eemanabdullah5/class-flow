# Manual Testing Checklist

Hands-on checks to run once the app is complete. Automated tests already cover these
rules. This list confirms them by hand and doubles as practice for the demo.

## Setup (every session)

```bash
# Terminal 1: backend
cd ~/Downloads/mini-project/classflow/backend
source .venv/bin/activate
python -m app.seed                 # safe to re-run, skips existing data
uvicorn app.main:app --reload

# Terminal 2: frontend
cd ~/Downloads/mini-project/classflow/frontend
npm run dev
```

- API docs: http://localhost:8000/docs (log in, copy `access_token`, click 🔒 **Authorize**, paste it)
- App: http://localhost:5173
- Demo accounts (password = `DEMO_PASSWORD` in `backend/.env`):
  `teacher@example.com`, `student1@example.com` (enrolled in course 1), `student2@example.com`
- Course 1 join code: `sqlite3 classflow.db "SELECT id, join_code FROM courses;"` (run in `backend/`)
- In `/docs`, any `{something}` in a path (e.g. `course_id`) has its own box in **Parameters**. Fill it in before **Execute**.

---

## 1. Assignments (Phase 4), in /docs

As **teacher**:
- [ ] `POST /api/courses/{course_id}/assignments`, `course_id` = 1:
  `{"title": "Assignment 1: Calculator", "instructions": "Write a calculator.", "max_points": 20, "due_at": "2026-11-30T23:59:00+05:00"}`
  → **201**, `due_at` shows `2026-11-30T18:59:00Z` (converted to UTC)
- [ ] Create a second one due sooner (`2026-11-05T23:59:00+05:00`) → list `GET /api/courses/1/assignments` shows it **first**
- [ ] Each of these gives **422**: due date in the past · no timezone (`2026-11-30T23:59:00`) · `max_points: 0` · extra `"category": "quiz"`
- [ ] `PATCH /api/assignments/1` with `{"title": "New title"}` → **200**, other fields unchanged

As **student1**:
- [ ] List and view assignments → **200**
- [ ] Create or PATCH an assignment → **403**

As an **outsider** (register a new student who hasn't joined course 1):
- [ ] List course 1 assignments → **404** · view assignment 1 → **404**

- [ ] Database: `sqlite3 -column classflow.db "SELECT id, title, due_at FROM assignments;"` shows UTC times

## 2. Submissions (Phase 5, step 1), in /docs

As **student1**:
- [ ] `PUT /api/assignments/1/submission`, **Choose File** → a PDF → **200**, `"status": "draft"`
- [ ] `POST /api/assignments/1/submission/turn-in` → `"status": "submitted"`, `"is_late": false`
- [ ] Upload again → **409** "Unsubmit first…"
- [ ] `POST .../unsubmit` → back to `draft`, then upload a new file → **200**, then turn in again
- [ ] Upload a `.txt` file → **415**
- [ ] `GET /api/assignments/1/my-submission` → your own submission
- [ ] `GET /api/submissions/{id}/file` → **Download file** link appears
- [ ] `backend/uploads/` contains a randomly named file (not your original filename)

As **student2** (join course 1 first if needed):
- [ ] `GET /api/assignments/1/my-submission` → `null` (can't see student1's)
- [ ] Download student1's submission id → **404**

As **teacher**:
- [ ] Download student1's file → works
- [ ] Upload a file → **403**

## 3. Grading (Phase 5, step 2), in /docs

As **teacher**:
- [ ] `GET /api/assignments/1/submissions` → every enrolled student; those who uploaded nothing show `"status": "missing"`
- [ ] `PUT /api/assignments/1/grades/{student1_id}` `{"score": 18, "feedback": "Good work"}` → **200**
- [ ] Score `25` (over max 20) → **422** · score `-1` → **422**
- [ ] Grade a student who hasn't submitted with `0` → **200**
- [ ] Grade a student whose work is still a **draft** before the deadline → **409**

As **student1**:
- [ ] `GET /api/assignments/1/my-grade` → score 18 and feedback
- [ ] `POST .../unsubmit` → **409** (graded work is locked)

As **student2**:
- [ ] `GET /api/assignments/1/my-grade` → `null` (or their own grade only)

## 4. Login and session (Phase 6, step 1), in the app at :5173

- [ ] Opening the app while logged out → sent to **Log in**
- [ ] Empty form → "Enter your email." / "Enter your password." (nothing sent)
- [ ] Wrong password → red box "Invalid email or password."
- [ ] Correct teacher login → welcome page, **teacher** badge in the navbar
- [ ] Refresh (Cmd+R) → still logged in
- [ ] **Log out** → login page with "You have been logged out."
- [ ] **Create an account**: mismatched passwords show an error; a valid sign-up lands on the welcome page as **student**
- [ ] Stop uvicorn, try to log in → "Can't reach the server. Is the backend running?"
- [ ] Inspect → Application → Session Storage shows `classflow_token`; close the tab and reopen → must log in again

## 5. Routing and page states (Phase 6, step 2), in the app at :5173

- [ ] Log in as **student1** → lands on **My courses**, showing the demo course card
- [ ] Type `localhost:5173/teacher` in the address bar → sent back to **My courses**
- [ ] Log in as **teacher** → lands on **Courses I teach**; typing `/student` → sent back
- [ ] Logged in, open `/login` → sent to your dashboard
- [ ] Open `/no-such-page` → **Page not found** with a link to the dashboard
- [ ] Log out, then open `/teacher` → login page; log in as teacher → lands back on `/teacher`
- [ ] Log in as a brand-new student → empty message "You haven't joined any courses yet."
- [ ] While on a dashboard, stop uvicorn and refresh → red error box with **Try again**; start uvicorn, click **Try again** → courses load
- [ ] Session expiry: in `backend/.env` set `JWT_EXPIRE_MINUTES=1`, restart uvicorn, log in, wait 1+ minute, refresh → "Your session has expired. Please log in again." Set it back to `60` afterwards.

## 6. Student side (Phase 6, step 3), in the app at :5173

First, as **teacher** in `/docs`, create an assignment in course 1 (see section 1), so students have something to open.

As **student2** (or a new student):
- [ ] Dashboard → **Join a course** with a wrong code → red "No course found with that code…"
- [ ] Join with the real code in lowercase → green "You joined …", the course card appears
- [ ] Click the course card → blue course header, assignment list with due dates in **your local time** and an **Assigned** badge
- [ ] Click an assignment → title, due date, points, instructions, **Your work** panel
- [ ] Choose a `.txt` file → Upload → "File type not allowed…" (nothing sent)
- [ ] Choose a PDF → **Upload** → file name and size appear, badge **Draft**, "not turned in yet"
- [ ] Choose another file → **Upload** again → replaces the draft
- [ ] **Download** → the file saves to your Downloads folder
- [ ] **Mark as done** → badge **Turned in**, upload box disappears, **Unsubmit** appears
- [ ] **Unsubmit** → back to **Draft**, "Replace file" box is back
- [ ] Back to the course → the badge matches
- [ ] After the teacher grades it (section 3) → the page shows the score (e.g. **18 / 20**), the feedback, and no Upload/Unsubmit buttons
- [ ] An assignment whose due date has passed with nothing turned in → **Missing** badge and a "due date has passed" warning
- [ ] Phone width: Inspect → device toolbar → iPhone; the pages still fit and stay readable

## 7. Later phases

Steps are added here as each phase is finished.
