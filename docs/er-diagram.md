# Database Relationship Diagram

This diagram shows every ClassFlow table, its columns and how the tables link together.
It matches the models in [`backend/app/models.py`](../backend/app/models.py).

```mermaid
erDiagram
    users ||--o{ courses : "teaches"
    users ||--o{ enrollments : "joins as student"
    courses ||--o{ enrollments : "has"
    courses ||--o{ assignments : "has"
    assignments ||--o{ submissions : "receives"
    users ||--o{ submissions : "uploads"
    assignments ||--o{ grades : "has"
    users ||--o{ grades : "is graded (student_id)"
    users ||--o{ grades : "grades (graded_by)"

    users {
        int id PK
        string email UK
        string full_name
        string password_hash
        string role "student or teacher"
        datetime created_at
    }

    courses {
        int id PK
        string title
        text description "optional"
        int teacher_id FK
        string join_code UK
        datetime created_at
    }

    enrollments {
        int id PK
        int course_id FK
        int student_id FK
        datetime enrolled_at
    }

    assignments {
        int id PK
        int course_id FK
        string title
        text instructions "optional"
        string category "assignment (MVP)"
        float max_points "greater than 0"
        datetime due_at
        datetime created_at
    }

    submissions {
        int id PK
        int assignment_id FK
        int student_id FK
        string status "draft or submitted"
        string original_filename
        string stored_filename UK
        string content_type
        int file_size "1 byte to 10 MB"
        datetime uploaded_at
        datetime submitted_at "empty while draft"
    }

    grades {
        int id PK
        int assignment_id FK
        int student_id FK
        float score "0 or more"
        text feedback "optional"
        int graded_by FK
        datetime graded_at
    }
```

## How to read it

- **PK** (primary key): the unique id of each row.
- **FK** (foreign key): must match an existing row in the linked table.
- **UK** (unique key): no two rows may have the same value.
- `||--o{` means **one to many**. For example, one course has zero or more assignments.

## Rules the diagram doesn't show

| Table | Rule | Why |
|---|---|---|
| enrollments | UNIQUE(course_id, student_id) | A student can't join the same course twice |
| submissions | UNIQUE(assignment_id, student_id) | One submission per student per assignment |
| submissions | status = 'submitted' needs submitted_at | We always know when work was turned in |
| grades | UNIQUE(assignment_id, student_id) | One grade per student per assignment |
| courses → enrollments, assignments | ON DELETE CASCADE | Deleting a course removes its enrollments and assignments |
| assignments → submissions, grades | ON DELETE CASCADE | Deleting an assignment removes its submissions and grades |
| any FK → users | no cascade | A user who still owns data can't be deleted |

**Many-to-many:** students and courses are linked through `enrollments`. One student can join many courses, and one course has many students.

**Why `grades` is separate from `submissions`:** some work, like an on-campus midterm (added later), gets a grade without any uploaded file.

## Checked in code, not in the database

- A course's `teacher_id` must belong to a user with role `teacher`.
- Only students enrolled in a course can submit to its assignments.
- `score` can't be greater than the assignment's `max_points`.
- No resubmitting after a grade exists.

## Tables added later with their features

- `topics`: the course topic tree. `parent_id` points to another topic.
- `topic_prerequisites`: the prerequisite graph between topics.
- `grade_changes`: the undo stack for grade edits.
