import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { STUDENT, fakeBackend, renderApp } from "./helpers.jsx";

const FUTURE = "2099-11-30T18:59:00Z";
const PAST = "2000-01-01T00:00:00Z";
const COURSE = { id: 1, title: "Programming Fundamentals", description: null, join_code: "ABC234", teacher_name: "Ms. Khan" };
const ASSIGNMENT = {
  id: 5,
  course_id: 1,
  title: "Assignment 1: Calculator",
  instructions: "Write a calculator.",
  category: "assignment",
  max_points: 20,
  due_at: FUTURE,
  created_at: PAST,
};

function submission(status) {
  return {
    id: 9,
    assignment_id: 5,
    student_id: STUDENT.id,
    status,
    original_filename: "homework.pdf",
    content_type: "application/pdf",
    file_size: 2048,
    uploaded_at: "2026-10-26T10:00:00Z",
    submitted_at: status === "submitted" ? "2026-10-26T11:00:00Z" : null,
    is_late: false,
  };
}

// ---------- joining a course ----------

describe("student dashboard", () => {
  it("joins a course with a code and shows it in the list", async () => {
    let joined = false;
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses": () => [200, joined ? [COURSE] : []],
      "POST /api/courses/join": () => {
        joined = true;
        return [201, COURSE];
      },
    });
    renderApp("/student", { loggedInAs: STUDENT });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Join a course"), "abc234");
    await user.click(screen.getByRole("button", { name: "Join" }));

    expect(await screen.findByText("You joined Programming Fundamentals.")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Programming Fundamentals/ })).toBeInTheDocument();
  });

  it("shows the backend's message for a wrong code", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses": [200, []],
      "POST /api/courses/join": [404, { detail: "No course found with that code. Check the code and try again." }],
    });
    renderApp("/student", { loggedInAs: STUDENT });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Join a course"), "WRONG1");
    await user.click(screen.getByRole("button", { name: "Join" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No course found with that code");
  });
});

// ---------- course page ----------

describe("course page (student)", () => {
  it("lists assignments with my status and grade", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses/1": [200, COURSE],
      "GET /api/courses/1/my-work": [
        200,
        [
          { assignment: { ...ASSIGNMENT, id: 1, title: "Hello World", due_at: PAST }, submission_status: "submitted", is_late: false, grade: { score: 17 } },
          { assignment: { ...ASSIGNMENT, id: 2, title: "Loops", due_at: PAST }, submission_status: "none", is_late: false, grade: null },
          { assignment: { ...ASSIGNMENT, id: 3, title: "Calculator" }, submission_status: "none", is_late: false, grade: null },
        ],
      ],
    });
    renderApp("/courses/1", { loggedInAs: STUDENT });

    const graded = await screen.findByRole("link", { name: /Hello World/ });
    expect(within(graded).getByText("Graded")).toBeInTheDocument();
    expect(within(graded).getByText("17/20")).toBeInTheDocument();
    expect(within(screen.getByRole("link", { name: /Loops/ })).getByText("Missing")).toBeInTheDocument();
    expect(within(screen.getByRole("link", { name: /Calculator/ })).getByText("Assigned")).toBeInTheDocument();
  });

  it("shows a clear message for a course the student can't see", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses/99": [404, { detail: "Course not found." }],
    });
    renderApp("/courses/99", { loggedInAs: STUDENT });

    expect(await screen.findByRole("alert")).toHaveTextContent("Course not found.");
  });
});

// ---------- assignment page: the upload flow ----------

function assignmentBackend({ work = null, grade = null } = {}) {
  const state = { work, grade };
  const fetchMock = fakeBackend({
    "GET /api/auth/me": [200, STUDENT],
    "GET /api/assignments/5": [200, ASSIGNMENT],
    "GET /api/assignments/5/my-submission": () => [200, state.work],
    "GET /api/assignments/5/my-grade": () => [200, state.grade],
    "PUT /api/assignments/5/submission": () => {
      state.work = submission("draft");
      return [200, state.work];
    },
    "POST /api/assignments/5/submission/turn-in": () => {
      state.work = submission("submitted");
      return [200, state.work];
    },
    "POST /api/assignments/5/submission/unsubmit": () => {
      state.work = submission("draft");
      return [200, state.work];
    },
  });
  return fetchMock;
}

function uploads(fetchMock) {
  return fetchMock.mock.calls.filter(([, options]) => options?.method === "PUT");
}

describe("assignment page (student)", () => {
  it("uploads a file, marks it as done, and can unsubmit", async () => {
    assignmentBackend();
    renderApp("/assignments/5", { loggedInAs: STUDENT });
    const user = userEvent.setup();

    expect(await screen.findByText("Assigned")).toBeInTheDocument();
    const pdf = new File(["%PDF-1.4 homework"], "homework.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Choose a file"), pdf);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText("homework.pdf")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mark as done" }));

    expect(await screen.findByText("Turned in")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Choose a file|Replace file/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Unsubmit" }));

    expect(await screen.findByText("Draft")).toBeInTheDocument();
    expect(screen.getByLabelText("Replace file")).toBeInTheDocument();
  });

  it("rejects a wrong file type before sending it", async () => {
    const fetchMock = assignmentBackend();
    renderApp("/assignments/5", { loggedInAs: STUDENT });
    const user = userEvent.setup({ applyAccept: false });

    const notes = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(await screen.findByLabelText("Choose a file"), notes);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("File type not allowed");
    expect(uploads(fetchMock)).toHaveLength(0);
  });

  it("shows the grade and feedback, and locks graded work", async () => {
    assignmentBackend({
      work: submission("submitted"),
      grade: { assignment_id: 5, student_id: 2, score: 18, feedback: "Nice work", graded_at: "2026-10-27T09:00:00Z" },
    });
    renderApp("/assignments/5", { loggedInAs: STUDENT });

    expect(await screen.findByText("18 / 20")).toBeInTheDocument();
    expect(screen.getByText("“Nice work”")).toBeInTheDocument();
    expect(screen.getByText("Graded")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Unsubmit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload" })).not.toBeInTheDocument();
  });
});
