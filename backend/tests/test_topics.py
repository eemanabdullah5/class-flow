import pytest
from sqlalchemy import func, select

from app.models import Course, Topic
from tests.conftest import auth_header


def add_topic(client, classroom, title="Python basics", parent_id=None, user_key="teacher", course=None):
    course = course or classroom["course"]
    body = {"title": title}
    if parent_id is not None:
        body["parent_id"] = parent_id
    return client.post(
        f"/api/courses/{course.id}/topics", json=body, headers=auth_header(classroom[user_key])
    )


def tree(client, classroom, user_key="teacher"):
    return client.get(
        f"/api/courses/{classroom['course'].id}/topics", headers=auth_header(classroom[user_key])
    )


def edit(client, classroom, topic_id, body, user_key="teacher"):
    return client.patch(f"/api/topics/{topic_id}", json=body, headers=auth_header(classroom[user_key]))


def remove(client, classroom, topic_id, user_key="teacher"):
    return client.delete(f"/api/topics/{topic_id}", headers=auth_header(classroom[user_key]))


def shape(nodes):
    """{title: {child title: {...}}}, so a whole tree can be checked at once."""
    return {node["title"]: shape(node["children"]) for node in nodes}


@pytest.fixture
def topics(client, classroom):
    """Python basics → Loops → For loops, plus Python basics → Functions, and a top-level Files."""
    ids = {}
    ids["basics"] = add_topic(client, classroom, "Python basics").json()["id"]
    ids["loops"] = add_topic(client, classroom, "Loops", ids["basics"]).json()["id"]
    ids["for"] = add_topic(client, classroom, "For loops", ids["loops"]).json()["id"]
    ids["functions"] = add_topic(client, classroom, "Functions", ids["basics"]).json()["id"]
    ids["files"] = add_topic(client, classroom, "Files").json()["id"]
    return ids


def other_course(session, classroom):
    """A second course owned by the same teacher."""
    course = Course(title="Databases", teacher_id=classroom["teacher"].id, join_code="DB5678")
    session.add(course)
    session.commit()
    return course


# ---------- adding topics ----------


def test_teacher_adds_a_top_level_topic(client, classroom):
    response = add_topic(client, classroom, "  Python basics  ")

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Python basics"  # spaces trimmed
    assert body["parent_id"] is None
    assert body["course_id"] == classroom["course"].id


def test_teacher_adds_a_subtopic(client, classroom):
    parent_id = add_topic(client, classroom).json()["id"]

    response = add_topic(client, classroom, "Loops", parent_id)

    assert response.status_code == 201
    assert response.json()["parent_id"] == parent_id


@pytest.mark.parametrize("title", ["", "   ", "x" * 151])
def test_bad_titles_are_rejected(client, classroom, title):
    assert add_topic(client, classroom, title).status_code == 422


def test_unknown_fields_are_rejected(client, classroom):
    response = client.post(
        f"/api/courses/{classroom['course'].id}/topics",
        json={"title": "Loops", "course_id": 999},
        headers=auth_header(classroom["teacher"]),
    )

    assert response.status_code == 422


def test_parent_must_exist(client, classroom):
    response = add_topic(client, classroom, "Loops", parent_id=999)

    assert response.status_code == 422
    assert response.json()["detail"] == "Parent topic must be a topic in this course."


def test_parent_must_be_in_the_same_course(client, session, classroom):
    databases = other_course(session, classroom)
    foreign_parent = add_topic(client, classroom, "SQL", course=databases).json()["id"]

    assert add_topic(client, classroom, "Loops", foreign_parent).status_code == 422


def test_student_cannot_add_a_topic(client, classroom):
    assert add_topic(client, classroom, user_key="student").status_code == 403


def test_other_teacher_cannot_add_a_topic(client, classroom):
    assert add_topic(client, classroom, user_key="other_teacher").status_code == 404


def test_adding_a_topic_needs_a_login(client, classroom):
    response = client.post(f"/api/courses/{classroom['course'].id}/topics", json={"title": "Loops"})

    assert response.status_code == 401


# ---------- reading the tree ----------


def test_tree_nests_subtopics_in_the_order_added(client, classroom, topics):
    response = tree(client, classroom)

    assert response.status_code == 200
    assert shape(response.json()) == {
        "Python basics": {"Loops": {"For loops": {}}, "Functions": {}},
        "Files": {},
    }
    assert [t["title"] for t in response.json()] == ["Python basics", "Files"]


def test_tree_nodes_show_ids_and_parents(client, classroom, topics):
    basics = tree(client, classroom).json()[0]

    assert basics["id"] == topics["basics"]
    assert basics["parent_id"] is None
    assert basics["children"][0]["parent_id"] == topics["basics"]


def test_course_without_topics_has_an_empty_tree(client, classroom):
    assert tree(client, classroom).json() == []


def test_enrolled_student_sees_the_tree(client, classroom, topics):
    response = tree(client, classroom, user_key="student")

    assert response.status_code == 200
    assert "Python basics" in shape(response.json())


@pytest.mark.parametrize("user_key", ["outsider", "other_teacher"])
def test_outsiders_cannot_see_the_tree(client, classroom, topics, user_key):
    assert tree(client, classroom, user_key=user_key).status_code == 404


def test_tree_only_shows_this_courses_topics(client, session, classroom, topics):
    add_topic(client, classroom, "SQL", course=other_course(session, classroom))

    assert "SQL" not in shape(tree(client, classroom).json())


# ---------- renaming and moving ----------


def test_teacher_renames_a_topic(client, classroom, topics):
    response = edit(client, classroom, topics["loops"], {"title": "Loops and ranges"})

    assert response.status_code == 200
    assert response.json()["title"] == "Loops and ranges"
    assert response.json()["parent_id"] == topics["basics"]  # not sent, so not moved


def test_teacher_moves_a_topic_with_its_subtopics(client, classroom, topics):
    response = edit(client, classroom, topics["loops"], {"parent_id": topics["files"]})

    assert response.status_code == 200
    assert shape(tree(client, classroom).json()) == {
        "Python basics": {"Functions": {}},
        "Files": {"Loops": {"For loops": {}}},
    }


def test_sending_null_parent_moves_to_top_level(client, classroom, topics):
    edit(client, classroom, topics["for"], {"parent_id": None})

    assert "For loops" in shape(tree(client, classroom).json())


@pytest.mark.parametrize("new_parent", ["basics", "loops", "for"])
def test_cannot_move_a_topic_inside_itself_or_its_subtopics(client, classroom, topics, new_parent):
    response = edit(client, classroom, topics["basics"], {"parent_id": topics[new_parent]})

    assert response.status_code == 409
    assert response.json()["detail"] == "A topic can't be moved inside itself or one of its own subtopics."
    assert shape(tree(client, classroom).json())["Python basics"]["Loops"] == {"For loops": {}}


def test_cannot_move_into_another_course(client, session, classroom, topics):
    foreign = add_topic(client, classroom, "SQL", course=other_course(session, classroom)).json()["id"]

    assert edit(client, classroom, topics["loops"], {"parent_id": foreign}).status_code == 422


@pytest.mark.parametrize("body", [{"title": ""}, {"title": None}, {"course_id": 2}])
def test_bad_edits_are_rejected(client, classroom, topics, body):
    assert edit(client, classroom, topics["loops"], body).status_code == 422


def test_student_cannot_edit_a_topic(client, classroom, topics):
    assert edit(client, classroom, topics["loops"], {"title": "Hacked"}, user_key="student").status_code == 403


def test_other_teacher_cannot_edit_a_topic(client, classroom, topics):
    response = edit(client, classroom, topics["loops"], {"title": "Hacked"}, user_key="other_teacher")

    assert response.status_code == 404
    assert response.json()["detail"] == "Topic not found."


def test_editing_a_missing_topic_gives_404(client, classroom):
    assert edit(client, classroom, 999, {"title": "Ghost"}).status_code == 404


# ---------- deleting ----------


def test_deleting_a_topic_deletes_its_subtopics(client, session, classroom, topics):
    response = remove(client, classroom, topics["basics"])

    assert response.status_code == 204
    assert shape(tree(client, classroom).json()) == {"Files": {}}
    assert session.scalar(select(func.count()).select_from(Topic)) == 1


def test_student_cannot_delete_a_topic(client, classroom, topics):
    assert remove(client, classroom, topics["files"], user_key="student").status_code == 403


def test_other_teacher_cannot_delete_a_topic(client, classroom, topics):
    assert remove(client, classroom, topics["files"], user_key="other_teacher").status_code == 404
    assert "Files" in shape(tree(client, classroom).json())


def test_deleting_needs_a_login(client, classroom, topics):
    assert client.delete(f"/api/topics/{topics['files']}").status_code == 401


def test_deleting_a_course_deletes_its_topics(client, session, classroom, topics):
    session.delete(classroom["course"])
    session.commit()

    assert session.scalar(select(func.count()).select_from(Topic)) == 0
