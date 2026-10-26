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
- **Database made before Phase 9?** Its old rule only allows the category "assignment", and `create_all()` never changes
  existing tables. Stop the server, delete `backend/classflow.db` (and the files in `backend/uploads/`), run
  `python -m app.seed` again, then start the server.

---

## 1. Assignments (Phase 4), in /docs

As **teacher**:
- [ ] `POST /api/courses/{course_id}/assignments`, `course_id` = 1:
  `{"title": "Assignment 1: Calculator", "instructions": "Write a calculator.", "max_points": 20, "due_at": "2026-11-30T23:59:00+05:00"}`
  → **201**, `due_at` shows `2026-11-30T18:59:00Z` (converted to UTC)
- [ ] Create a second one due sooner (`2026-11-05T23:59:00+05:00`) → list `GET /api/courses/1/assignments` shows it **first**
- [ ] Each of these gives **422**: due date in the past · no timezone (`2026-11-30T23:59:00`) · `max_points: 0` · `"category": "exam"` (not one of the four)
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

## 7. Teacher side (Phase 6, step 4), in the app at :5173

As **teacher**:
- [ ] Dashboard → **Create course** with an empty title → "Enter a course title."
- [ ] Create "Object Oriented Programming" → green message with the join code; the card shows "Join code: …"
- [ ] Open the course → big **join code** with **Copy** (paste somewhere to check), assignment list, **Students** roster
- [ ] **+ New assignment** with nothing filled in → three red errors; a past due date → "The due date must be in the future."
- [ ] Create one (title, instructions, 20 points, a date next week at 11:59 PM) → appears in the list showing **your local time**
- [ ] Open it → **Edit** → change only the title → **Save changes** → title updated, due date unchanged
- [ ] **Student work** shows every enrolled student; those with nothing show "No file uploaded."

Full workflow (two browsers, or one normal window plus one private window, so both people can be logged in):
- [ ] Teacher creates a course → student joins with the code → student appears in the roster
- [ ] Teacher creates an assignment → student sees it as **Assigned**
- [ ] Student uploads and clicks **Mark as done** → teacher refreshes → **Turned in**, the summary line counts it
- [ ] Teacher **Download**s the student's file → it opens correctly
- [ ] Teacher enters **25** → "Enter a score from 0 to 20." · enters **18** + feedback → **Grade saved.**, badge **Graded**
- [ ] Student refreshes → sees **18 / 20** and the feedback; Unsubmit is gone
- [ ] Teacher changes it to **19** → **Update grade** → student sees 19
- [ ] A student with a **Draft** (uploaded, not marked done) before the deadline → teacher's save shows "still a draft…"

## 8. Polish (Phase 6, step 5), in the app at :5173

- [ ] Browser tabs show the page name, e.g. "Programming Fundamentals · ClassFlow", plus the blue "C" icon
- [ ] Navbar has a **Dashboard** link that's underlined while you're on the dashboard
- [ ] Press **Tab** once on any page → a blue "Skip to main content" button appears top-left; Enter jumps past the navbar
- [ ] Keep pressing Tab → every link, button and input shows a clear blue outline, and nothing is skipped
- [ ] Course cards and assignment rows can be opened with Tab + Enter
- [ ] Register with a very long name and upload a file with a very long filename → text wraps, no sideways scrolling
- [ ] Phone width (Inspect → device toolbar → iPhone SE): navbar fits, forms are full width, grade form fields stack, join code box wraps
- [ ] macOS System Settings → Accessibility → Display → **Reduce motion** on → the loading spinner stops spinning

## 9. Grade undo (Phase 7), in the app at :5173

Log in as the teacher and open an assignment where `student1` has turned in work.

- [ ] Nothing graded yet → the blue bar says "No grade changes to undo." and **Undo last grade change** is greyed out
- [ ] Give the student **12** → the bar shows "Sara Ahmed: 12 → no grade" (with your student's name) and the button works
- [ ] Change it to **15**, then **18** → the bar shows "18 → 15"
- [ ] **Undo** → "Undone: … 18 → 15", the score box shows **15**, and the bar now shows "15 → 12"
- [ ] **Undo** again → score box **12** · **Undo** again → score box empty, badge back to **Turned in**, button greyed out
- [ ] As the student (second window): after the last undo, refresh → no grade, and **Unsubmit** is back (work unlocked)
- [ ] Give feedback only (same score, new feedback) → it can be undone; saving the exact same score and feedback again adds nothing to undo
- [ ] Grade on assignment A, then open assignment B → the bar names assignment A ("… on Assignment A: …"); undo there → A's grade is undone
- [ ] Refresh the page after an undo → it stays undone (it was saved, not just hidden); there is no redo
- [ ] Second teacher (`python -m app.create_teacher --email teacher2@example.com --name "Mr. Ali"` in `backend/`):
      log in as them → "No grade changes to undo." even right after the first teacher graded
- [ ] In `/docs` as a student: `GET /api/grades/undo` and `POST /api/grades/undo` → **403**; with no login → **401**

## 10. Topics and prerequisites (Phase 8), in the app at :5173

As the teacher, open a course → **Topics and study order**.
- [ ] No topics yet → "No topics yet. Add the first topic above."; the Study order section isn't shown
- [ ] **Add topic** with an empty title → "Enter a topic title." and nothing is added
- [ ] Add **Python basics**; then choose it in **Put inside** and add **Variables**, **Loops**, **Functions** → they appear indented under it
- [ ] Inside **Loops**, add **For loops** → two levels deep; add a top-level **Files**
- [ ] **Edit** Loops → rename to "Loops and ranges" → **Save** → the new name shows in the tree and the study order
- [ ] **Edit** Python basics → **Put inside** doesn't list Python basics or any of its subtopics (only Top level and Files)
- [ ] **Edit** For loops → Put inside **Files** → Save → it moves with nothing lost · move it back to **Top level** → it's at the top
- [ ] **Edit** Loops → add prerequisite **Variables** → tree shows "Needs: Variables"; study order lists Variables before Loops
- [ ] **Edit** Functions → add **Loops** and **Variables** → allowed (a diamond, not a loop)
- [ ] **Edit** Variables → add **Functions** → red box: 'That would make a loop: "Variables" needs "Functions" needs … "Variables".' and nothing changes
- [ ] **Remove** a prerequisite → "Needs:" line updates; the reverse arrow is now allowed
- [ ] **Delete topic** on Python basics → the confirm box says how many subtopics go with it · **Cancel** → nothing happens · **OK** → it and its subtopics are gone, and their prerequisite arrows too
- [ ] As the enrolled student: the course page has the **Topics and study order** link; the tree and study order show, with no Add form or Edit buttons
- [ ] As `student2` (not enrolled): open `/courses/1/topics` directly → "Course not found."
- [ ] Phone width: the topic editor's fields stack and nothing scrolls sideways
- [ ] In `/docs` as a student: `POST /api/courses/1/topics` → **403**; as another teacher → **404**

## 11. Weighted results, letter grades, stats and reports (Phase 9)

Setup: as the teacher, create one of each category in a course with **two enrolled students** (register a second student
and join with the code): Quiz (10 pts), Assignment (20 pts), Midterm (50 pts), Project (100 pts). Give them due dates in
the near future (a few minutes ahead), so that some can pass while you test.

Categories and in-class work:
- [ ] **+ New assignment** → the **Category** dropdown lists Quiz 10%, Assignment 10%, Midterm 30% (taken in class), Project 50%
- [ ] Lists and the assignment page show the category, e.g. "Quiz · Due …"; the midterm page says "Midterm · In class …"
- [ ] As a student, open the midterm → **Your mark** with "This is taken in class…", no file upload, badge **In class**
- [ ] As the teacher, open the midterm → each row says "Taken in class: enter the mark below." and has no Download
- [ ] Teacher enters a midterm mark **before** its date → saved (in-class work doesn't wait for a hand-in)
- [ ] An assignment a student uploaded a file to → **Edit** → Category **Midterm** → "Students have already uploaded work…"

My result (student):
- [ ] Before anything is graded or due → "No result yet…"
- [ ] Student A: quiz **8/10**, assignment handed in and graded **15/20**, midterm **35/50** → **73% B, Passing**;
      the table shows Quiz 8 / 10 · 80%, Project "–"
- [ ] Student B: quiz past due with nothing handed in → it counts as **0/10** → **0% F, "Not passing yet (50% needed)"**;
      hand in the assignment late without a grade → it doesn't count yet (still "–")
- [ ] Give student B quiz 5/10 → their result changes to 50% **D, Passing** (exactly 50% passes)

Results and reports page (teacher → course page → **Results and reports**):
- [ ] **Class statistics:** count, average, lowest, highest, variance (population) and % passing match your numbers
- [ ] **Course results:** one row per student with each category %, overall, letter and Yes/No; the letter scale is listed
- [ ] **Report 1:** each assignment with turned in / late / missing / graded and average, lowest–highest; midterm missing says "in class"
- [ ] **Report 2:** each student's handed-in, late and graded counts, and points of graded work (e.g. 58 / 80)
- [ ] **Report 3:** missing (nothing or only a draft after the deadline) and late work; the assignment link opens it;
      grade the missing quiz with 0 → it leaves the list
- [ ] As student1, go to `/courses/1/results` → sent back to the dashboard; in `/docs` the results/report endpoints give **403**,
      and **404** for another teacher
- [ ] Phone width: the wide tables scroll inside their box; the page itself doesn't scroll sideways

## 12. Later phases

Steps are added here as each phase is finished.
