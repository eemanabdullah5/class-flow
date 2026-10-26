import pytest
from sqlalchemy import func, select

from app.models import Course, TopicPrerequisite
from tests.conftest import auth_header
from tests.test_topics import add_topic, remove, tree


def need(client, classroom, topic_id, prerequisite_id, user_key="teacher"):
    """Say "topic_id needs prerequisite_id first"."""
    return client.post(
        f"/api/topics/{topic_id}/prerequisites",
        json={"prerequisite_id": prerequisite_id},
        headers=auth_header(classroom[user_key]),
    )


def unneed(client, classroom, topic_id, prerequisite_id, user_key="teacher"):
    return client.delete(
        f"/api/topics/{topic_id}/prerequisites/{prerequisite_id}", headers=auth_header(classroom[user_key])
    )


def study_order(client, classroom, user_key="teacher"):
    return client.get(
        f"/api/courses/{classroom['course'].id}/topics/study-order", headers=auth_header(classroom[user_key])
    )


def titles_in_order(client, classroom):
    return [item["title"] for item in study_order(client, classroom).json()]


def arrow_count(session):
    return session.scalar(select(func.count()).select_from(TopicPrerequisite))


@pytest.fixture
def topics(client, classroom):
    """Four top-level topics, added in this order, with no prerequisites yet."""
    return {
        title: add_topic(client, classroom, title).json()["id"]
        for title in ["Functions", "Loops", "Variables", "Recursion"]
    }


# ---------- adding prerequisites ----------


def test_teacher_adds_a_prerequisite(client, classroom, topics):
    response = need(client, classroom, topics["Loops"], topics["Variables"])

    assert response.status_code == 201
    assert response.json() == {"topic_id": topics["Loops"], "prerequisite_ids": [topics["Variables"]]}


def test_a_topic_can_have_several_prerequisites(client, classroom, topics):
    need(client, classroom, topics["Functions"], topics["Variables"])

    response = need(client, classroom, topics["Functions"], topics["Loops"])

    assert response.json()["prerequisite_ids"] == [topics["Variables"], topics["Loops"]]


def test_tree_shows_each_topics_prerequisites(client, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])

    nodes = {node["title"]: node for node in tree(client, classroom).json()}

    assert nodes["Loops"]["prerequisite_ids"] == [topics["Variables"]]
    assert nodes["Variables"]["prerequisite_ids"] == []


def test_a_subtopic_can_need_a_topic_elsewhere_in_the_tree(client, classroom, topics):
    for_loops = add_topic(client, classroom, "For loops", topics["Loops"]).json()["id"]

    assert need(client, classroom, for_loops, topics["Variables"]).status_code == 201


def test_topic_cannot_be_its_own_prerequisite(client, classroom, topics):
    response = need(client, classroom, topics["Loops"], topics["Loops"])

    assert response.status_code == 422
    assert response.json()["detail"] == "A topic can't be its own prerequisite."


def test_same_prerequisite_twice_is_refused(client, session, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])

    response = need(client, classroom, topics["Loops"], topics["Variables"])

    assert response.status_code == 409
    assert response.json()["detail"] == '"Variables" is already a prerequisite of "Loops".'
    assert arrow_count(session) == 1


@pytest.mark.parametrize("prerequisite_id", [999, "other course"])
def test_prerequisite_must_be_a_topic_in_the_same_course(client, session, classroom, topics, prerequisite_id):
    if prerequisite_id == "other course":
        databases = Course(title="Databases", teacher_id=classroom["teacher"].id, join_code="DB5678")
        session.add(databases)
        session.commit()
        prerequisite_id = add_topic(client, classroom, "SQL", course=databases).json()["id"]

    response = need(client, classroom, topics["Loops"], prerequisite_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "Prerequisite must be a topic in this course."


def test_body_must_be_just_a_prerequisite_id(client, classroom, topics):
    response = client.post(
        f"/api/topics/{topics['Loops']}/prerequisites",
        json={"prerequisite_id": topics["Variables"], "topic_id": 1},
        headers=auth_header(classroom["teacher"]),
    )

    assert response.status_code == 422


# ---------- cycles are refused ----------


def test_two_topics_cannot_need_each_other(client, session, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])

    response = need(client, classroom, topics["Variables"], topics["Loops"])

    assert response.status_code == 409
    assert response.json()["detail"] == 'That would make a loop: "Variables" needs "Loops" needs "Variables".'
    assert arrow_count(session) == 1  # nothing was saved


def test_a_longer_loop_is_refused_and_shown_in_full(client, classroom, topics):
    need(client, classroom, topics["Recursion"], topics["Functions"])
    need(client, classroom, topics["Functions"], topics["Loops"])
    need(client, classroom, topics["Loops"], topics["Variables"])

    response = need(client, classroom, topics["Variables"], topics["Recursion"])

    assert response.status_code == 409
    assert response.json()["detail"] == (
        'That would make a loop: "Variables" needs "Recursion" needs "Functions" '
        'needs "Loops" needs "Variables".'
    )


def test_diamond_shape_is_allowed(client, classroom, topics):
    # Functions needs Loops and Variables; Loops also needs Variables. No loop.
    need(client, classroom, topics["Loops"], topics["Variables"])
    need(client, classroom, topics["Functions"], topics["Variables"])

    assert need(client, classroom, topics["Functions"], topics["Loops"]).status_code == 201


def test_after_removing_an_arrow_the_reverse_is_allowed(client, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])
    unneed(client, classroom, topics["Loops"], topics["Variables"])

    assert need(client, classroom, topics["Variables"], topics["Loops"]).status_code == 201


# ---------- study order ----------


def test_study_order_puts_prerequisites_first(client, classroom, topics):
    need(client, classroom, topics["Recursion"], topics["Functions"])
    need(client, classroom, topics["Functions"], topics["Loops"])
    need(client, classroom, topics["Loops"], topics["Variables"])

    assert titles_in_order(client, classroom) == ["Variables", "Loops", "Functions", "Recursion"]


def test_study_order_without_prerequisites_is_the_order_added(client, classroom, topics):
    assert titles_in_order(client, classroom) == ["Functions", "Loops", "Variables", "Recursion"]


def test_study_order_items_list_their_prerequisites(client, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])

    items = {item["title"]: item for item in study_order(client, classroom).json()}

    assert items["Loops"]["prerequisite_ids"] == [topics["Variables"]]
    assert items["Loops"]["parent_id"] is None


def test_study_order_includes_subtopics(client, classroom, topics):
    add_topic(client, classroom, "For loops", topics["Loops"])

    assert "For loops" in titles_in_order(client, classroom)


def test_empty_course_has_an_empty_study_order(client, classroom):
    assert study_order(client, classroom).json() == []


def test_enrolled_student_sees_the_study_order(client, classroom, topics):
    assert study_order(client, classroom, user_key="student").status_code == 200


@pytest.mark.parametrize("user_key", ["outsider", "other_teacher"])
def test_outsiders_cannot_see_the_study_order(client, classroom, topics, user_key):
    assert study_order(client, classroom, user_key=user_key).status_code == 404


# ---------- removing prerequisites ----------


def test_teacher_removes_a_prerequisite(client, session, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])

    response = unneed(client, classroom, topics["Loops"], topics["Variables"])

    assert response.status_code == 204
    assert arrow_count(session) == 0


def test_removing_a_prerequisite_that_isnt_there_gives_404(client, classroom, topics):
    response = unneed(client, classroom, topics["Loops"], topics["Variables"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Prerequisite not found."


def test_deleting_a_topic_removes_its_arrows_both_ways(client, session, classroom, topics):
    need(client, classroom, topics["Loops"], topics["Variables"])
    need(client, classroom, topics["Functions"], topics["Loops"])

    remove(client, classroom, topics["Loops"])

    assert arrow_count(session) == 0
    assert titles_in_order(client, classroom) == ["Functions", "Variables", "Recursion"]


# ---------- permissions ----------


def test_student_cannot_add_or_remove_prerequisites(client, session, classroom, topics):
    assert need(client, classroom, topics["Loops"], topics["Variables"], user_key="student").status_code == 403
    need(client, classroom, topics["Loops"], topics["Variables"])
    assert unneed(client, classroom, topics["Loops"], topics["Variables"], user_key="student").status_code == 403
    assert arrow_count(session) == 1


def test_other_teacher_cannot_add_or_remove_prerequisites(client, session, classroom, topics):
    response = need(client, classroom, topics["Loops"], topics["Variables"], user_key="other_teacher")
    assert response.status_code == 404
    need(client, classroom, topics["Loops"], topics["Variables"])
    assert unneed(client, classroom, topics["Loops"], topics["Variables"], user_key="other_teacher").status_code == 404
    assert arrow_count(session) == 1


def test_prerequisites_need_a_login(client, classroom, topics):
    url = f"/api/topics/{topics['Loops']}/prerequisites"

    assert client.post(url, json={"prerequisite_id": topics["Variables"]}).status_code == 401
    assert client.delete(f"{url}/{topics['Variables']}").status_code == 401
    assert client.get(f"/api/courses/{classroom['course'].id}/topics/study-order").status_code == 401
