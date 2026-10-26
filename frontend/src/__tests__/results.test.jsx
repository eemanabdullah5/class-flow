import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { formatPercent, isInClass } from "../utils/categories.js";
import { STUDENT, TEACHER, fakeBackend, renderApp } from "./helpers.jsx";

const PAST = "2000-01-01T00:00:00Z";
const FUTURE = "2099-11-30T18:59:00Z";
const COURSE = { id: 1, title: "Programming Fundamentals", description: null, join_code: "ABC234", teacher_name: "Ms. Khan" };
const ALI = { id: 3, email: "ali@example.com", full_name: "Ali Raza", role: "student" };

const category = (name, weight, earned, possible) => ({
  category: name,
  weight,
  earned,
  possible,
  percentage: possible ? (100 * earned) / possible : null,
});

// Sara: 73% B passing (quiz 8/10, assignment 15/20, midterm 35/50, no project yet)
const SARA_RESULT = {
  percentage: 73,
  letter: "B",
  passed: true,
  categories: [
    category("quiz", 10, 8, 10),
    category("assignment", 10, 15, 20),
    category("midterm", 30, 35, 50),
    category("project", 50, null, null),
  ],
};
const ALI_RESULT = {
  percentage: 0,
  letter: "F",
  passed: false,
  categories: [category("quiz", 10, 0, 10), category("assignment", 10, null, null), category("midterm", 30, null, null), category("project", 50, null, null)],
};
const NO_RESULT = { percentage: null, letter: null, passed: null, categories: ALI_RESULT.categories.map((c) => ({ ...c, earned: null, possible: null, percentage: null })) };

describe("helpers", () => {
  it("formats percentages", () => {
    expect(formatPercent(73)).toBe("73%");
    expect(formatPercent(62.5)).toBe("62.5%");
    expect(formatPercent(66.666)).toBe("66.7%");
    expect(formatPercent(null)).toBe("–");
  });

  it("knows the midterm is taken in class", () => {
    expect(isInClass("midterm")).toBe(true);
    expect(isInClass("quiz")).toBe(false);
  });
});

// ---------- students ----------

function studentCourse(result) {
  return fakeBackend({
    "GET /api/auth/me": [200, STUDENT],
    "GET /api/courses/1": [200, COURSE],
    "GET /api/courses/1/my-work": [200, []],
    "GET /api/courses/1/my-result": [200, result],
  });
}

describe("my result (student)", () => {
  it("shows my weighted result, letter and each category", async () => {
    studentCourse(SARA_RESULT);
    renderApp("/courses/1", { loggedInAs: STUDENT });

    const card = within((await screen.findByRole("heading", { name: "My result" })).closest("section"));
    expect(card.getByText("73%")).toBeInTheDocument();
    expect(card.getByText("B")).toBeInTheDocument();
    expect(card.getByText("Passing")).toBeInTheDocument();
    const quiz = card.getByRole("row", { name: /Quiz/ });
    expect(within(quiz).getByText("8 / 10")).toBeInTheDocument();
    expect(within(quiz).getByText("80%")).toBeInTheDocument();
    const project = card.getByRole("row", { name: /Project/ });
    expect(within(project).getAllByText("–")).toHaveLength(2); // nothing counted yet
  });

  it("says when I'm not passing", async () => {
    studentCourse(ALI_RESULT);
    renderApp("/courses/1", { loggedInAs: STUDENT });

    expect(await screen.findByText("Not passing yet (50% needed)")).toBeInTheDocument();
    expect(screen.getByText("F")).toBeInTheDocument();
  });

  it("explains when there is no result yet", async () => {
    studentCourse(NO_RESULT);
    renderApp("/courses/1", { loggedInAs: STUDENT });

    expect(await screen.findByText(/No result yet/)).toBeInTheDocument();
  });

  it("can't open the teacher's results page", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses": [200, []],
    });
    renderApp("/courses/1/results", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: /My courses/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Results and reports" })).not.toBeInTheDocument();
  });
});

describe("midterm (in-class work)", () => {
  const MIDTERM = { id: 7, course_id: 1, title: "Midterm", instructions: null, category: "midterm", max_points: 50, due_at: PAST, created_at: PAST };

  it("has no upload for the student, just the mark when it's entered", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/assignments/7": [200, MIDTERM],
      "GET /api/assignments/7/my-submission": [200, null],
      "GET /api/assignments/7/my-grade": [200, null],
    });
    renderApp("/assignments/7", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: "Your mark" })).toBeInTheDocument();
    expect(screen.getByText(/taken in class, so there is nothing to upload/)).toBeInTheDocument();
    expect(screen.getByText("Waiting for marks")).toBeInTheDocument();
    expect(screen.queryByLabelText("Choose a file")).not.toBeInTheDocument();
    expect(screen.queryByText(/will be marked late/)).not.toBeInTheDocument();
    expect(screen.getByText(/Midterm · In class/)).toBeInTheDocument();
  });

  it("shows the student's mark once entered", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/assignments/7": [200, MIDTERM],
      "GET /api/assignments/7/my-submission": [200, null],
      "GET /api/assignments/7/my-grade": [200, { assignment_id: 7, student_id: 2, score: 35, feedback: "Well done", graded_at: PAST }],
    });
    renderApp("/assignments/7", { loggedInAs: STUDENT });

    expect(await screen.findByText("35 / 50")).toBeInTheDocument();
    expect(screen.getByText("Graded")).toBeInTheDocument();
  });

  it("lets the teacher enter marks without any file", async () => {
    fakeBackend({
      "GET /api/auth/me": [200, TEACHER],
      "GET /api/assignments/7": [200, MIDTERM],
      "GET /api/assignments/7/submissions": [200, [{ student: STUDENT, status: "missing", submission: null, grade: null }]],
      "GET /api/grades/undo": [200, null],
    });
    renderApp("/assignments/7", { loggedInAs: TEACHER });

    const row = (await screen.findByText(STUDENT.full_name, { selector: "strong" })).closest("li");
    expect(within(row).getByText("Taken in class: enter the mark below.")).toBeInTheDocument();
    expect(within(row).getByText("Waiting for marks")).toBeInTheDocument();
    expect(within(row).queryByText("No file uploaded.")).not.toBeInTheDocument();
    expect(within(row).getByLabelText("Score (out of 50)")).toBeInTheDocument();
    expect(screen.getByText(/0 missing/)).toBeInTheDocument();
  });
});

// ---------- teachers ----------

const CLASS_RESULTS = {
  pass_percent: 50,
  letter_scale: [
    { lowest: 80, letter: "A" },
    { lowest: 70, letter: "B" },
    { lowest: 60, letter: "C" },
    { lowest: 50, letter: "D" },
    { lowest: 0, letter: "F" },
  ],
  students: [
    { student: STUDENT, result: SARA_RESULT },
    { student: ALI, result: ALI_RESULT },
  ],
  stats: { count: 2, mean: 36.5, minimum: 0, maximum: 73, variance: 1332.25, pass_proportion: 0.5 },
};

const ASSIGNMENT_REPORT = [
  {
    id: 1, title: "Quiz 1", category: "quiz", max_points: 10, due_at: PAST, enrolled: 2, turned_in: 0, late: 0,
    missing: 1, graded: 1, average_score: 8, lowest_score: 8, highest_score: 8,
  },
  {
    id: 3, title: "Midterm", category: "midterm", max_points: 50, due_at: PAST, enrolled: 2, turned_in: 0, late: 0,
    missing: null, graded: 1, average_score: 35, lowest_score: 35, highest_score: 35,
  },
  {
    id: 4, title: "Project", category: "project", max_points: 100, due_at: FUTURE, enrolled: 2, turned_in: 0, late: 0,
    missing: 0, graded: 0, average_score: null, lowest_score: null, highest_score: null,
  },
];
const STUDENT_REPORT = [
  { id: 2, full_name: STUDENT.full_name, email: STUDENT.email, turned_in: 1, late: 0, graded: 3, points_earned: 58, points_possible: 80 },
  { id: 3, full_name: ALI.full_name, email: ALI.email, turned_in: 1, late: 1, graded: 0, points_earned: 0, points_possible: 0 },
];
const MISSING_LATE = [
  { student_id: 3, student_name: "Ali Raza", assignment_id: 1, assignment_title: "Quiz 1", category: "quiz", due_at: PAST, submitted_at: null, problem: "missing" },
  { student_id: 3, student_name: "Ali Raza", assignment_id: 2, assignment_title: "Homework 1", category: "assignment", due_at: PAST, submitted_at: PAST, problem: "late" },
];

function resultsBackend(changes = {}) {
  return fakeBackend({
    "GET /api/auth/me": [200, TEACHER],
    "GET /api/courses/1": [200, COURSE],
    "GET /api/courses/1/assignments": [200, []],
    "GET /api/courses/1/students": [200, []],
    "GET /api/courses/1/results": [200, CLASS_RESULTS],
    "GET /api/courses/1/reports/assignments": [200, ASSIGNMENT_REPORT],
    "GET /api/courses/1/reports/students": [200, STUDENT_REPORT],
    "GET /api/courses/1/reports/missing-late": [200, MISSING_LATE],
    ...changes,
  });
}

function section(name) {
  return within(screen.getByRole("heading", { name }).closest("section"));
}

describe("results and reports page (teacher)", () => {
  it("is reached from the course page", async () => {
    resultsBackend();
    renderApp("/courses/1", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: /Results and reports/ }));

    expect(await screen.findByRole("heading", { name: "Results and reports" })).toBeInTheDocument();
  });

  it("shows the class statistics", async () => {
    resultsBackend();
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    await screen.findByText("36.5%");
    const stats = section("Class statistics");
    const value = (label) => stats.getByText(label).closest(".stat-card").querySelector("dd").textContent;
    expect(value("Students with a result")).toBe("2");
    expect(value("Average")).toBe("36.5%");
    expect(value("Lowest")).toBe("0%");
    expect(value("Highest")).toBe("73%");
    expect(value("Variance")).toBe("1332.25");
    expect(value("Passing (50%+)")).toBe("50%");
  });

  it("lists each student's weighted result and the letter scale", async () => {
    resultsBackend();
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    await screen.findByText("36.5%");
    const results = section("Course results");
    const sara = results.getByRole("row", { name: /Sara Ahmed/ });
    expect(within(sara).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["80%", "75%", "70%", "–", "73%", "B", "Yes"]);
    const ali = results.getByRole("row", { name: /Ali Raza/ });
    expect(within(ali).getByText("No")).toBeInTheDocument();
    expect(results.getByText(/A 80%\+, B 70%\+, C 60%\+, D 50%\+, F 0%\+/)).toBeInTheDocument();
  });

  it("shows the three reports", async () => {
    resultsBackend();
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    await screen.findByText("36.5%");
    const byAssignment = section("Report 1: Assignment summary");
    const quiz = byAssignment.getByRole("row", { name: /Quiz 1/ });
    expect(within(quiz).getAllByText("1 / 2")).toHaveLength(1); // graded
    expect(within(quiz).getByText("0 / 2")).toBeInTheDocument(); // turned in
    expect(within(byAssignment.getByRole("row", { name: /Midterm/ })).getByText("in class")).toBeInTheDocument();

    const byStudent = section("Report 2: Student progress");
    expect(within(byStudent.getByRole("row", { name: /Sara Ahmed/ })).getByText("58 / 80")).toBeInTheDocument();

    const problems = section("Report 3: Missing and late work");
    expect(problems.getByRole("link", { name: "Quiz 1" })).toHaveAttribute("href", "/assignments/1");
    expect(problems.getByText("Missing")).toBeInTheDocument();
    expect(problems.getByText(/^Late ·/)).toBeInTheDocument();
  });

  it("says when nothing is missing or late", async () => {
    resultsBackend({ "GET /api/courses/1/reports/missing-late": [200, []] });
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    expect(await screen.findByText("Nothing missing or late.")).toBeInTheDocument();
  });

  it("keeps the other parts when one report fails", async () => {
    resultsBackend({ "GET /api/courses/1/reports/students": [500, { detail: "Something broke." }] });
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");
    expect(within(screen.getByRole("alert")).getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(section("Report 3: Missing and late work").getByText("Missing")).toBeInTheDocument();
  });

  it("shows the backend's message for someone else's course", async () => {
    resultsBackend({ "GET /api/courses/1": [404, { detail: "Course not found." }] });
    renderApp("/courses/1/results", { loggedInAs: TEACHER });

    expect(await screen.findByRole("alert")).toHaveTextContent("Course not found.");
  });
});
