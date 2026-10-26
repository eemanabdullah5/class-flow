from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_course_for_member, get_course_for_owner, get_topic_for_owner
from app.database import get_db
from app.deps import get_current_user, require_teacher
from app.models import Topic, User
from app.schemas import TopicCreate, TopicNode, TopicOut, TopicUpdate
from app.tree import build_tree, would_create_loop

router = APIRouter(tags=["topics"])

PARENT_NOT_IN_COURSE = "Parent topic must be a topic in this course."
MOVE_INTO_ITSELF = "A topic can't be moved inside itself or one of its own subtopics."


def course_topics(db: Session, course_id: int) -> list[Topic]:
    """All of a course's topics, flat, in the order they were added."""
    return db.scalars(select(Topic).where(Topic.course_id == course_id).order_by(Topic.id)).all()


def check_parent(db: Session, course_id: int, parent_id: int | None) -> None:
    """A parent must be an existing topic of the same course (or None for top level)."""
    if parent_id is None:
        return
    parent = db.get(Topic, parent_id)
    if parent is None or parent.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PARENT_NOT_IN_COURSE)


def to_node(node: dict) -> TopicNode:
    topic = node["item"]
    return TopicNode(
        id=topic.id,
        parent_id=topic.parent_id,
        title=topic.title,
        children=[to_node(child) for child in node["children"]],
    )


@router.post(
    "/api/courses/{course_id}/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED
)
def create_topic(
    course_id: int,
    data: TopicCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Only the teacher who owns the course. Leave parent_id out for a top-level topic."""
    get_course_for_owner(db, course_id, teacher)
    check_parent(db, course_id, data.parent_id)
    topic = Topic(course_id=course_id, **data.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.get("/api/courses/{course_id}/topics", response_model=list[TopicNode])
def get_topic_tree(
    course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The course's whole topic tree: top-level topics, each with its subtopics inside.

    The course's teacher or an enrolled student. Anyone else gets 404.
    """
    get_course_for_member(db, course_id, user)
    tree = build_tree(course_topics(db, course_id), lambda t: t.id, lambda t: t.parent_id)
    return [to_node(node) for node in tree]


@router.patch("/api/topics/{topic_id}", response_model=TopicOut)
def update_topic(
    topic_id: int,
    data: TopicUpdate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Rename and/or move a topic. Only the course's teacher."""
    topic = get_topic_for_owner(db, topic_id, teacher)
    changes = data.model_dump(exclude_unset=True)

    if "parent_id" in changes:
        new_parent_id = changes["parent_id"]
        check_parent(db, topic.course_id, new_parent_id)
        parent_of = {t.id: t.parent_id for t in course_topics(db, topic.course_id)}
        if would_create_loop(parent_of, topic.id, new_parent_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MOVE_INTO_ITSELF)

    for field, value in changes.items():
        setattr(topic, field, value)
    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/api/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """Delete a topic and all its subtopics. Only the course's teacher."""
    topic = get_topic_for_owner(db, topic_id, teacher)
    db.delete(topic)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
