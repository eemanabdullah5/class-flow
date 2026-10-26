from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.security import MAX_PASSWORD_BYTES

# Pydantic models describe the exact shape of data coming in and going out.
# FastAPI checks every request against them and replies 422 if the data is invalid.


class RegisterRequest(BaseModel):
    # "forbid" rejects unknown fields, so sending {"role": "teacher"} fails with 422.
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        return email.lower()

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, full_name: str) -> str:
        full_name = full_name.strip()
        if not full_name:
            raise ValueError("Full name cannot be blank.")
        return full_name

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        # Some characters (e.g. emoji) use several bytes, so check bytes, not just length.
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        return email.lower()


class UserOut(BaseModel):
    """What the API shows about a user. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)  # can be built from a User model object

    id: int
    email: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CourseCreate(BaseModel):
    # "forbid" stops a client from sneaking in fields like teacher_id or join_code.
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError("Title cannot be blank.")
        return title


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    join_code: str
    teacher_name: str


class JoinCourseRequest(BaseModel):
    join_code: str = Field(min_length=1, max_length=20)

    @field_validator("join_code")
    @classmethod
    def tidy_join_code(cls, join_code: str) -> str:
        # Accept " abc123 " as "ABC123", so small typing differences don't matter.
        return join_code.strip().upper()


MAX_ASSIGNMENT_POINTS = 1000


def require_future(due_at: datetime) -> datetime:
    if due_at <= datetime.now(timezone.utc):
        raise ValueError("Due date must be in the future.")
    return due_at


def reject_nulls(model: BaseModel, fields: list[str]) -> None:
    """For edit (PATCH) bodies: a field may be left out, but a required one can't be sent as null."""
    for field in fields:
        if field in model.model_fields_set and getattr(model, field) is None:
            raise ValueError(f"{field.replace('_', ' ').capitalize()} cannot be empty.")


def strip_required_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValueError("Title cannot be blank.")
    return title


# quiz 10% · assignment 10% · midterm 30% (in class, no upload) · project 50%; see app/scoring.py
Category = Literal["quiz", "assignment", "midterm", "project"]


class AssignmentCreate(BaseModel):
    # course_id comes from the URL, so it may not be sent in the body.
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    category: Category = "assignment"
    instructions: str | None = Field(default=None, max_length=5000)
    max_points: float = Field(gt=0, le=MAX_ASSIGNMENT_POINTS)
    # AwareDatetime: the time must include a timezone, e.g. "2026-11-01T23:59:00Z"
    # or "2026-11-02T04:59:00+05:00". A bare "2026-11-01T23:59" is rejected.
    due_at: AwareDatetime

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        return strip_required_title(title)

    @field_validator("due_at")
    @classmethod
    def future_due(cls, due_at: datetime) -> datetime:
        return require_future(due_at)


class AssignmentUpdate(BaseModel):
    """Every field is optional: only the fields that are sent get changed."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=150)
    category: Category | None = None
    instructions: str | None = Field(default=None, max_length=5000)
    max_points: float | None = Field(default=None, gt=0, le=MAX_ASSIGNMENT_POINTS)
    due_at: AwareDatetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str | None) -> str | None:
        return None if title is None else strip_required_title(title)

    @field_validator("due_at")
    @classmethod
    def future_due(cls, due_at: datetime | None) -> datetime | None:
        return None if due_at is None else require_future(due_at)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        # instructions may be cleared with null; the others are required.
        reject_nulls(self, ["title", "category", "max_points", "due_at"])
        return self


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    instructions: str | None
    category: str
    max_points: float
    due_at: datetime
    created_at: datetime


class TopicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    parent_id: int | None = None  # empty = a top-level topic

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        return strip_required_title(title)


class TopicUpdate(BaseModel):
    """Rename and/or move. Sending "parent_id": null moves the topic to the top level;
    leaving parent_id out keeps it where it is."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=150)
    parent_id: int | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str | None) -> str | None:
        return None if title is None else strip_required_title(title)

    @model_validator(mode="after")
    def title_not_null(self):
        # parent_id may be sent as null (move to top level), but a title can't be removed.
        reject_nulls(self, ["title"])
        return self


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    parent_id: int | None
    title: str


class TopicNode(BaseModel):
    """A topic with its subtopics inside it, for showing the whole tree."""

    id: int
    parent_id: int | None
    title: str
    prerequisite_ids: list[int]  # topics to learn before this one
    children: list["TopicNode"]


class PrerequisiteAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prerequisite_id: int


class TopicPrerequisites(BaseModel):
    topic_id: int
    prerequisite_ids: list[int]


class StudyOrderItem(BaseModel):
    """One topic in the suggested study order: every prerequisite comes earlier in the list."""

    id: int
    parent_id: int | None
    title: str
    prerequisite_ids: list[int]


class SubmissionOut(BaseModel):
    """A submission as the API shows it. The random stored filename is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    student_id: int
    status: str
    original_filename: str
    content_type: str
    file_size: int
    uploaded_at: datetime
    submitted_at: datetime | None
    is_late: bool


class GradeSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The upper limit depends on the assignment's max_points, so it is checked in the router.
    score: float = Field(ge=0)
    feedback: str | None = Field(default=None, max_length=2000)


class GradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    student_id: int
    score: float
    feedback: str | None
    graded_at: datetime


class GradeUndoPreview(BaseModel):
    """What undo would do (or just did), e.g. "Sara Ahmed: 18 -> no grade"."""

    assignment_id: int
    assignment_title: str
    student_id: int
    student_name: str
    from_score: float  # the grade before undo
    to_score: float | None  # the grade after undo; None means "no grade"


class StudentWorkRow(BaseModel):
    """One row of the teacher's list: an enrolled student and where their work stands."""

    student: UserOut
    status: str  # "missing", "draft" or "submitted"
    submission: SubmissionOut | None
    grade: GradeOut | None


class MyWorkRow(BaseModel):
    """One assignment in a course, with where the logged-in student's own work stands."""

    assignment: AssignmentOut
    submission_status: str  # "none", "draft" or "submitted"
    is_late: bool
    grade: GradeOut | None


# ---------- results, stats and reports (Phase 9) ----------


class CategoryResult(BaseModel):
    category: str
    weight: int  # percent of the course result
    earned: float | None  # None: nothing in this category counts yet
    possible: float | None
    percentage: float | None


class CourseResult(BaseModel):
    """None everywhere means nothing counts yet (no grades, nothing missing)."""

    percentage: float | None
    letter: str | None
    passed: bool | None
    categories: list[CategoryResult]


class StudentResultRow(BaseModel):
    student: UserOut
    result: CourseResult


class ClassStats(BaseModel):
    """Over students who have a result. All None (except count) when nobody has one yet."""

    count: int
    mean: float | None
    minimum: float | None
    maximum: float | None
    variance: float | None  # population variance of the percentages
    pass_proportion: float | None  # 0.0 to 1.0


class LetterBand(BaseModel):
    lowest: float  # lowest percent that gets this letter
    letter: str


class ClassResults(BaseModel):
    pass_percent: int
    letter_scale: list[LetterBand]  # highest letter first
    students: list[StudentResultRow]
    stats: ClassStats


class AssignmentReportRow(BaseModel):
    id: int
    title: str
    category: str
    max_points: float
    due_at: datetime
    enrolled: int
    turned_in: int
    late: int
    missing: int | None  # None for in-class work (nothing to hand in)
    graded: int
    average_score: float | None
    lowest_score: float | None
    highest_score: float | None


class StudentReportRow(BaseModel):
    id: int
    full_name: str
    email: str
    turned_in: int
    late: int
    graded: int
    points_earned: float
    points_possible: float  # max points of the graded work only


class MissingLateRow(BaseModel):
    student_id: int
    student_name: str
    assignment_id: int
    assignment_title: str
    category: str
    due_at: datetime
    submitted_at: datetime | None
    problem: Literal["missing", "late"]
