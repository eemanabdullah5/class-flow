from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_course_for_member, get_course_for_owner, get_topic_for_owner
from app.database import get_db
from app.deps import get_current_user, require_teacher
from app.graph import CycleError, dependency_order, would_create_cycle
from app.models import Topic, TopicPrerequisite, User
from app.schemas import (
    PrerequisiteAdd,
    StudyOrderItem,
    TopicCreate,
    TopicNode,
    TopicOut,
    TopicPrerequisites,
    TopicUpdate,
)
from app.tree import build_tree, would_create_loop

router = APIRouter(tags=["topics"])

PARENT_NOT_IN_COURSE = "Parent topic must be a topic in this course."
MOVE_INTO_ITSELF = "A topic can't be moved inside itself or one of its own subtopics."
PREREQUISITE_NOT_IN_COURSE = "Prerequisite must be a topic in this course."


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


def prerequisite_graph(db: Session, course_id: int) -> dict[int, list[int]]:
    """The course's prerequisite graph: {topic id: [ids of topics it needs first]}.

    Every topic is in the dict (with [] if it needs nothing), in the order the arrows were added.
    """
    graph = {topic.id: [] for topic in course_topics(db, course_id)}
    arrows = db.scalars(
        select(TopicPrerequisite)
        .join(Topic, Topic.id == TopicPrerequisite.topic_id)
        .where(Topic.course_id == course_id)
        .order_by(TopicPrerequisite.id)
    )
    for arrow in arrows:
        graph[arrow.topic_id].append(arrow.prerequisite_id)
    return graph


def to_node(node: dict, graph: dict[int, list[int]]) -> TopicNode:
    topic = node["item"]
    return TopicNode(
        id=topic.id,
        parent_id=topic.parent_id,
        title=topic.title,
        prerequisite_ids=graph.get(topic.id, []),
        children=[to_node(child, graph) for child in node["children"]],
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
    graph = prerequisite_graph(db, course_id)
    tree = build_tree(course_topics(db, course_id), lambda t: t.id, lambda t: t.parent_id)
    return [to_node(node, graph) for node in tree]


@router.get("/api/courses/{course_id}/topics/study-order", response_model=list[StudyOrderItem])
def get_study_order(
    course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Every topic, flat, in an order where each topic's prerequisites come first.

    Topics with no prerequisites between them stay in the order they were added.
    The course's teacher or an enrolled student.
    """
    get_course_for_member(db, course_id, user)
    topics = {topic.id: topic for topic in course_topics(db, course_id)}
    graph = prerequisite_graph(db, course_id)
    try:
        order = dependency_order(list(topics), graph)
    except CycleError:  # can't happen: loops are refused when arrows are added
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The prerequisites contain a loop."
        )
    return [
        StudyOrderItem(
            id=topic_id,
            parent_id=topics[topic_id].parent_id,
            title=topics[topic_id].title,
            prerequisite_ids=graph[topic_id],
        )
        for topic_id in order
    ]


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


# ---------- prerequisites: "learn topic B before topic A" ----------


@router.post(
    "/api/topics/{topic_id}/prerequisites",
    response_model=TopicPrerequisites,
    status_code=status.HTTP_201_CREATED,
)
def add_prerequisite(
    topic_id: int,
    data: PrerequisiteAdd,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Say that this topic needs another topic of the same course learned first.

    Refused if it would make a loop, e.g. Loops needs Functions while Functions needs Loops.
    Only the course's teacher.
    """
    topic = get_topic_for_owner(db, topic_id, teacher)
    prerequisite = db.get(Topic, data.prerequisite_id)
    if prerequisite is None or prerequisite.course_id != topic.course_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PREREQUISITE_NOT_IN_COURSE
        )
    if prerequisite.id == topic.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A topic can't be its own prerequisite.",
        )

    graph = prerequisite_graph(db, topic.course_id)
    if prerequisite.id in graph[topic.id]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'"{prerequisite.title}" is already a prerequisite of "{topic.title}".',
        )
    cycle = would_create_cycle(graph, topic.id, prerequisite.id)
    if cycle:
        titles = {t.id: t.title for t in course_topics(db, topic.course_id)}
        chain = " needs ".join(f'"{titles[node]}"' for node in cycle)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"That would make a loop: {chain}."
        )

    db.add(TopicPrerequisite(topic_id=topic.id, prerequisite_id=prerequisite.id))
    db.commit()
    return TopicPrerequisites(topic_id=topic.id, prerequisite_ids=graph[topic.id] + [prerequisite.id])


@router.delete(
    "/api/topics/{topic_id}/prerequisites/{prerequisite_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_prerequisite(
    topic_id: int,
    prerequisite_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Remove one "needs first" arrow. Only the course's teacher."""
    get_topic_for_owner(db, topic_id, teacher)
    arrow = db.scalars(
        select(TopicPrerequisite).where(
            TopicPrerequisite.topic_id == topic_id, TopicPrerequisite.prerequisite_id == prerequisite_id
        )
    ).first()
    if arrow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prerequisite not found.")
    db.delete(arrow)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
