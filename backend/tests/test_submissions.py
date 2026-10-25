from datetime import datetime, timedelta, timezone

import pytest

from app.models import MAX_UPLOAD_BYTES, Grade
from tests.conftest import auth_header

PDF = b"%PDF-1.4\nthis is a pretend homework file\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"pretend image data"
EXE = b"MZ\x90\x00" + b"pretend windows program"  # what a real .exe starts with


def upload(client, classroom, user_key="student", filename="homework.pdf", data=PDF):
    return client.put(
        f"/api/assignments/{classroom['assignment'].id}/submission",
        files={"file": (filename, data, "application/pdf")},
        headers=auth_header(classroom[user_key]),
    )


def action(client, classroom, name, user_key="student"):
    """name is "turn-in" or "unsubmit"."""
    return client.post(
        f"/api/assignments/{classroom['assignment'].id}/submission/{name}",
        headers=auth_header(classroom[user_key]),
    )


def my_submission(client, classroom, user_key="student"):
    return client.get(
        f"/api/assignments/{classroom['assignment'].id}/my-submission",
        headers=auth_header(classroom[user_key]),
    )


def files_on_disk(upload_dir):
    return sorted(p.name for p in upload_dir.iterdir()) if upload_dir.exists() else []


def give_grade(session, classroom):
    session.add(
        Grade(
            assignment_id=classroom["assignment"].id,
            student_id=classroom["student"].id,
            score=18,
            graded_by=classroom["teacher"].id,
        )
    )
    session.commit()


# ---------- uploading ----------


def test_upload_creates_a_draft_saved_under_a_random_name(client, classroom, temporary_upload_dir):
    response = upload(client, classroom)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["original_filename"] == "homework.pdf"
    assert body["file_size"] == len(PDF)
    assert body["submitted_at"] is None
    assert "stored_filename" not in body  # the real name on disk stays private

    [stored] = files_on_disk(temporary_upload_dir)
    assert stored != "homework.pdf" and stored.endswith(".pdf")
    assert (temporary_upload_dir / stored).read_bytes() == PDF


def test_png_is_accepted(client, classroom):
    assert upload(client, classroom, filename="diagram.PNG", data=PNG).status_code == 200


@pytest.mark.parametrize(
    "filename, data, expected_status",
    [
        ("virus.exe", EXE, 415),  # type not allowed
        ("homework.pdf", EXE, 415),  # a program renamed to .pdf
        ("photo.png", PDF, 415),  # contents don't match the extension
        ("notes.txt", b"hello", 415),
        ("homework.pdf", b"", 422),  # empty
        ("homework.pdf", b"%PDF-" + b"0" * MAX_UPLOAD_BYTES, 413),  # just over 10 MB
    ],
)
def test_bad_files_are_rejected_and_nothing_is_kept(
    client, classroom, temporary_upload_dir, filename, data, expected_status
):
    response = upload(client, classroom, filename=filename, data=data)

    assert response.status_code == expected_status
    assert files_on_disk(temporary_upload_dir) == []
    assert my_submission(client, classroom).json() is None


def test_path_tricks_in_the_filename_are_harmless(client, classroom, temporary_upload_dir):
    response = upload(client, classroom, filename="../../../etc/evil.pdf")

    assert response.status_code == 200
    assert response.json()["original_filename"] == "evil.pdf"
    assert len(files_on_disk(temporary_upload_dir)) == 1  # saved inside the upload folder


def test_replacing_a_draft_deletes_the_old_file(client, classroom, temporary_upload_dir):
    upload(client, classroom, filename="first.pdf")
    [first_stored] = files_on_disk(temporary_upload_dir)

    response = upload(client, classroom, filename="second.pdf")

    assert response.json()["original_filename"] == "second.pdf"
    assert files_on_disk(temporary_upload_dir) != [first_stored]
    assert len(files_on_disk(temporary_upload_dir)) == 1


# ---------- mark as done / unsubmit ----------


def test_marking_as_done_records_the_time(client, classroom):
    upload(client, classroom)

    response = action(client, classroom, "turn-in")

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert response.json()["submitted_at"] is not None
    assert response.json()["is_late"] is False


def test_cannot_mark_as_done_without_a_file(client, classroom):
    response = action(client, classroom, "turn-in")

    assert response.status_code == 409
    assert response.json()["detail"] == "Upload a file before marking the work as done."


def test_submitted_file_must_be_unsubmitted_before_replacing(client, classroom):
    upload(client, classroom)
    action(client, classroom, "turn-in")

    assert upload(client, classroom, filename="better.pdf").status_code == 409

    unsubmitted = action(client, classroom, "unsubmit")
    assert unsubmitted.json()["status"] == "draft"
    assert unsubmitted.json()["submitted_at"] is None
    assert upload(client, classroom, filename="better.pdf").status_code == 200


def test_work_turned_in_after_the_due_date_is_flagged_late(client, session, classroom):
    upload(client, classroom)
    classroom["assignment"].due_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.commit()

    response = action(client, classroom, "turn-in")

    assert response.status_code == 200  # late work is still accepted
    assert response.json()["is_late"] is True


def test_graded_work_is_locked(client, session, classroom):
    upload(client, classroom)
    action(client, classroom, "turn-in")
    give_grade(session, classroom)

    assert action(client, classroom, "unsubmit").status_code == 409
    assert upload(client, classroom, filename="sneaky.pdf").status_code == 409


# ---------- who may upload ----------


def test_teacher_cannot_upload(client, classroom):
    assert upload(client, classroom, user_key="teacher").status_code == 403


def test_student_not_in_the_course_gets_404(client, classroom):
    assert upload(client, classroom, user_key="outsider").status_code == 404
    assert my_submission(client, classroom, user_key="outsider").status_code == 404


# ---------- seeing only your own ----------


def test_my_submission_is_null_before_uploading(client, classroom):
    response = my_submission(client, classroom)

    assert response.status_code == 200
    assert response.json() is None


def test_classmate_does_not_see_my_submission(client, classroom):
    upload(client, classroom)

    assert my_submission(client, classroom, user_key="student").json()["original_filename"] == "homework.pdf"
    assert my_submission(client, classroom, user_key="classmate").json() is None


# ---------- downloading ----------


def download(client, classroom, submission_id, user_key):
    return client.get(f"/api/submissions/{submission_id}/file", headers=auth_header(classroom[user_key]))


@pytest.mark.parametrize("user_key", ["student", "teacher"])
def test_owner_and_teacher_can_download_as_an_attachment(client, classroom, user_key):
    submission_id = upload(client, classroom).json()["id"]

    response = download(client, classroom, submission_id, user_key)

    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment")
    assert 'filename="homework.pdf"' in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("user_key", ["classmate", "outsider", "other_teacher"])
def test_nobody_else_can_download(client, classroom, user_key):
    submission_id = upload(client, classroom).json()["id"]

    response = download(client, classroom, submission_id, user_key)

    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found."


def test_download_requires_login(client, classroom):
    submission_id = upload(client, classroom).json()["id"]

    assert client.get(f"/api/submissions/{submission_id}/file").status_code == 401
