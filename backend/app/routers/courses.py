from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_course_for_member, get_course_for_owner, is_enrolled
from app.database import get_db
from app.deps import get_current_user, require_student, require_teacher
from app.models import Course, Enrollment, User
from app.schemas import CourseCreate, CourseOut, JoinCourseRequest, UserOut
from app.services.courses import generate_join_code

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    data: CourseCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Teachers only. The logged-in teacher becomes the owner; the join code is generated."""
    course = Course(
        title=data.title,
        description=data.description,
        teacher_id=teacher.id,
        join_code=generate_join_code(db),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
def list_my_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Teachers see the courses they teach. Students see the courses they have joined."""
    if user.role == "teacher":
        query = select(Course).where(Course.teacher_id == user.id)
    else:
        query = (
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == user.id)
        )
    return db.scalars(query.order_by(Course.id)).all()


@router.post("/join", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def join_course(
    data: JoinCourseRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Students only. Join a course using the code the teacher shared."""
    course = db.scalars(select(Course).where(Course.join_code == data.join_code)).first()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No course found with that code. Check the code and try again.",
        )
    if is_enrolled(db, course.id, student.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You are already enrolled in this course."
        )

    db.add(Enrollment(course_id=course.id, student_id=student.id))
    db.commit()
    return course


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The course's teacher or an enrolled student. Anyone else gets 404."""
    return get_course_for_member(db, course_id, user)


@router.get("/{course_id}/students", response_model=list[UserOut])
def list_course_students(
    course_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    """The class roster. Only the teacher who owns the course."""
    get_course_for_owner(db, course_id, teacher)
    return db.scalars(
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
        .order_by(User.full_name)
    ).all()
