# ClassFlow — Student Assignment and Progress Tracker

A small Google Classroom–inspired web app where teachers create courses, assignments and grades, and students join courses, upload work and track their progress.

> **Status:** planning. The folder structure below is the agreed target; folders are created as each phase is implemented.

## Tech stack

| Layer    | Technology                                   |
|----------|----------------------------------------------|
| Frontend | React (JavaScript), Vite, React Router       |
| Backend  | Python, FastAPI                              |
| Database | SQLite, accessed through SQLAlchemy (ORM)    |
| Testing  | pytest (backend), Vitest + React Testing Library (frontend) |
| Version control | Git                                   |

## Folder structure

```
classflow/
├── README.md
├── .gitignore                    # ignores .env, *.db, uploads/, .venv/, node_modules/, __pycache__/
├── docs/
│   ├── er-diagram.md             # database relationship diagram (Mermaid)
│   ├── security.md               # token storage, expiry, logout, file-upload rules
│   └── demo-plan.md              # step-by-step demonstration script
│
├── backend/
│   ├── .env.example              # placeholder values only — never real secrets
│   ├── requirements.txt
│   ├── uploads/                  # uploaded submission files (git-ignored, never served directly)
│   ├── app/
│   │   ├── main.py               # creates the FastAPI app and includes the routers
│   │   ├── config.py             # reads environment variables; refuses to start without JWT_SECRET
│   │   ├── database.py           # SQLAlchemy engine, session, get_db(), foreign keys ON
│   │   ├── models.py             # ORM classes: User, Course, Enrollment, Assignment, Submission, Grade, ...
│   │   ├── schemas.py            # Pydantic request/response models (validation)
│   │   ├── security.py           # password hashing, JWT create/verify
│   │   ├── deps.py               # get_current_user, require_teacher, require_student
│   │   ├── routers/              # HTTP endpoints, one file per area
│   │   │   ├── auth.py
│   │   │   ├── courses.py
│   │   │   ├── assignments.py
│   │   │   ├── submissions.py
│   │   │   ├── grades.py
│   │   │   ├── topics.py
│   │   │   └── reports.py
│   │   ├── services/             # plain Python logic, testable without HTTP
│   │   │   ├── grading.py        # weighted category scores, pass/fail
│   │   │   ├── stats.py          # mean, min, max, population variance, pass proportion
│   │   │   ├── tree.py           # topic tree building
│   │   │   ├── graph.py          # prerequisite retrieval and cycle detection
│   │   │   ├── undo.py           # grade-change undo stack
│   │   │   └── files.py          # safe file saving (size/type checks, random names)
│   │   ├── seed.py               # creates demo teacher/student accounts and sample data
│   │   └── create_teacher.py     # command-line script to add a real teacher account
│   └── tests/
│       ├── conftest.py           # fresh test database per test, test client, login helpers
│       └── test_*.py
│
└── frontend/
    ├── package.json
    ├── vite.config.js            # dev proxy: /api -> http://localhost:8000
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx               # route definitions
        ├── api/
        │   └── client.js         # the single place that calls fetch; adds token, handles 401
        ├── auth/
        │   ├── AuthContext.jsx   # logged-in user, login(), logout()
        │   └── ProtectedRoute.jsx
        ├── hooks/
        │   └── useApi.js         # loading / error / data pattern
        ├── components/           # Button, FormField, Loading, EmptyState, ErrorMessage, NavBar, ...
        ├── pages/                # Login, Register, StudentDashboard, TeacherDashboard, CourseDetail, ...
        └── __tests__/
```
