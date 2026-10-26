import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { localInputToIso, toLocalInputValue } from "../utils/dates.js";
import { STUDENT, TEACHER, fakeBackend, renderApp } from "./helpers.jsx";

const FUTURE = "2099-11-30T18:59:00Z";
const PAST = "2000-01-01T00:00:00Z";
const COURSE = { id: 1, title: "Programming Fundamentals", description: null, join_code: "ABC234", teacher_name: "Ms. Khan" };
const ASSIGNMENT = {
  id: 5,
  course_id: 1,
  title: "Assignment 1",
  instructions: null,
  category: "assignment",
  max_points: 20,
  due_at: FUTURE,
  created_at: PAST,
};

function bodyOf(fetchMock, method, path) {
  const call = fetchMock.mock.calls.find(([p, options]) => p === path && options?.method === method);
  return call ? JSON.parse(call[1].body) : undefined;
}

function callsTo(fetchMock, method) {
  return fetchMock.mock.calls.filter(([, options]) => options?.method === method);
}

// ---------- dashboard ----------

describe("teacher dashboard", () => {
  it("creates a course and shows its join code", async () => {
    let created = false;
    const fetchMock = fakeBackend({
      "GET /api/auth/me": [200, TEACHER],
      "GET /api/courses": () => [200, created ? [COURSE] : []],
      "POST /api/courses": () => {
        created = true;
        return [201, COURSE];
      },
    });
    renderApp("/teacher", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Course title"), "Programming Fundamentals");
    await user.click(screen.getByRole("button", { name: "Create course" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Share the join code ABC234");
    expect(await screen.findByText("Join code: ABC234")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "POST", "/api/courses")).toEqual({ title: "Programming Fundamentals", description: null });
  });

  it("asks for a title before sending", async () => {
    const fetchMock = fakeBackend({ "GET /api/auth/me": [200, TEACHER], "GET /api/courses": [200, []] });
    renderApp("/teacher", { loggedInAs: TEACHER });

    await userEvent.setup().click(await screen.findByRole("button", { name: "Create course" }));

    expect(screen.getByText("Enter a course title.")).toBeInTheDocument();
    expect(callsTo(fetchMock, "POST")).toHaveLength(0);
  });
});

// ---------- course page ----------

function courseBackend(extra = {}) {
  let assignments = [];
  return fakeBackend({
    "GET /api/auth/me": [200, TEACHER],
    "GET /api/courses/1": [200, COURSE],
    "GET /api/courses/1/assignments": () => [200, assignments],
    "GET /api/courses/1/students": [200, [STUDENT]],
    "POST /api/courses/1/assignments": (options) => {
      const body = JSON.parse(options.body);
      assignments = [{ ...ASSIGNMENT, ...body }];
      return [201, assignments[0]];
    },
    ...extra,
  });
}

describe("course page (teacher)", () => {
  it("shows the join code and the class roster", async () => {
    courseBackend();
    renderApp("/courses/1", { loggedInAs: TEACHER });

    expect(await screen.findByText("ABC234")).toBeInTheDocument();
    expect(await screen.findByText(STUDENT.full_name)).toBeInTheDocument();
    expect(screen.getByText("No assignments yet.")).toBeInTheDocument();
  });

  it("creates an assignment, sending the due date in UTC", async () => {
    const fetchMock = courseBackend();
    renderApp("/courses/1", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "+ New assignment" }));
    await user.type(screen.getByLabelText("Title"), "Calculator");
    await user.type(screen.getByLabelText("Max points"), "20");
    fireEvent.change(screen.getByLabelText("Due date (your local time)"), {
      target: { value: "2099-11-30T23:59" },
    });
    await user.click(screen.getByRole("button", { name: "Create assignment" }));

    expect(await screen.findByRole("link", { name: /Calculator/ })).toBeInTheDocument();
    expect(bodyOf(fetchMock, "POST", "/api/courses/1/assignments")).toEqual({
      title: "Calculator",
      instructions: null,
      max_points: 20,
      due_at: localInputToIso("2099-11-30T23:59"),
    });
  });

  it("checks the assignment form before sending", async () => {
    const fetchMock = courseBackend();
    renderApp("/courses/1", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "+ New assignment" }));
    fireEvent.change(screen.getByLabelText("Due date (your local time)"), {
      target: { value: "2001-01-01T10:00" },
    });
    await user.click(screen.getByRole("button", { name: "Create assignment" }));

    expect(screen.getByText("Enter a title.")).toBeInTheDocument();
    expect(screen.getByText(/Max points must be more than 0/)).toBeInTheDocument();
    expect(screen.getByText("The due date must be in the future.")).toBeInTheDocument();
    expect(callsTo(fetchMock, "POST")).toHaveLength(0);
  });
});

// ---------- assignment page: grading ----------

const SUBMITTED = {
  id: 9,
  assignment_id: 5,
  student_id: 2,
  status: "submitted",
  original_filename: "homework.pdf",
  content_type: "application/pdf",
  file_size: 2048,
  uploaded_at: "2026-10-26T10:00:00Z",
  submitted_at: "2026-10-26T11:00:00Z",
  is_late: false,
};
const ALI = { id: 3, email: "ali@example.com", full_name: "Ali Raza", role: "student" };

function gradingBackend({ putResponse } = {}) {
  let grade = null;
  return fakeBackend({
    "GET /api/auth/me": [200, TEACHER],
    "GET /api/assignments/5": [200, ASSIGNMENT],
    "GET /api/assignments/5/submissions": () => [
      200,
      [
        { student: ALI, status: "missing", submission: null, grade: null },
        { student: STUDENT, status: "submitted", submission: SUBMITTED, grade },
      ],
    ],
    "PUT /api/assignments/5/grades/2": (options) => {
      if (putResponse) return putResponse;
      const body = JSON.parse(options.body);
      grade = { assignment_id: 5, student_id: 2, ...body, graded_at: "2026-10-27T09:00:00Z" };
      return [200, grade];
    },
  });
}

describe("assignment page (teacher)", () => {
  it("lists every student, including those who handed in nothing", async () => {
    gradingBackend();
    renderApp("/assignments/5", { loggedInAs: TEACHER });

    const ali = (await screen.findByText("Ali Raza")).closest("li");
    expect(within(ali).getByText("No file uploaded.")).toBeInTheDocument();
    expect(within(ali).getByText("Assigned")).toBeInTheDocument();
    const sara = screen.getByText(STUDENT.full_name).closest("li");
    expect(within(sara).getByText("homework.pdf")).toBeInTheDocument();
    expect(within(sara).getByText("Turned in")).toBeInTheDocument();
  });

  it("grades a student and shows them as graded", async () => {
    const fetchMock = gradingBackend();
    renderApp("/assignments/5", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const sara = (await screen.findByText(STUDENT.full_name)).closest("li");
    await user.type(within(sara).getByLabelText("Score (out of 20)"), "18");
    await user.type(within(sara).getByLabelText("Feedback (optional)"), "Nice work");
    await user.click(within(sara).getByRole("button", { name: "Save grade" }));

    expect(await within(sara).findByText("Grade saved.")).toBeInTheDocument();
    expect(await within(sara).findByText("Graded")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "PUT", "/api/assignments/5/grades/2")).toEqual({ score: 18, feedback: "Nice work" });
  });

  it("refuses a score above the maximum before sending", async () => {
    const fetchMock = gradingBackend();
    renderApp("/assignments/5", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const sara = (await screen.findByText(STUDENT.full_name)).closest("li");
    await user.type(within(sara).getByLabelText("Score (out of 20)"), "25");
    await user.click(within(sara).getByRole("button", { name: "Save grade" }));

    expect(within(sara).getByRole("alert")).toHaveTextContent("Enter a score from 0 to 20.");
    expect(callsTo(fetchMock, "PUT")).toHaveLength(0);
  });

  it("shows the backend's reason when grading is refused", async () => {
    gradingBackend({
      putResponse: [409, { detail: "This student's work is still a draft. Wait until they mark it as done." }],
    });
    renderApp("/assignments/5", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const sara = (await screen.findByText(STUDENT.full_name)).closest("li");
    await user.type(within(sara).getByLabelText("Score (out of 20)"), "15");
    await user.click(within(sara).getByRole("button", { name: "Save grade" }));

    expect(await within(sara).findByRole("alert")).toHaveTextContent("still a draft");
  });

  it("edits only the fields that changed", async () => {
    const fetchMock = fakeBackend({
      "GET /api/auth/me": [200, TEACHER],
      "GET /api/assignments/5": [200, ASSIGNMENT],
      "GET /api/assignments/5/submissions": [200, []],
      "PATCH /api/assignments/5": [200, { ...ASSIGNMENT, title: "Assignment 1 (v2)" }],
    });
    renderApp("/assignments/5", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Edit" }));
    expect(screen.getByLabelText("Due date (your local time)")).toHaveValue(toLocalInputValue(FUTURE));
    await user.type(screen.getByLabelText("Title"), " (v2)");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await screen.findByRole("button", { name: "Edit" });
    expect(bodyOf(fetchMock, "PATCH", "/api/assignments/5")).toEqual({ title: "Assignment 1 (v2)" });
  });
});
