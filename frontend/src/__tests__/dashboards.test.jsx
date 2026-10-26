import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { STUDENT, TEACHER, fakeBackend, renderApp } from "./helpers.jsx";

const COURSE = { id: 1, title: "Programming Fundamentals", description: null, join_code: "ABC234", teacher_name: "Ms. Khan" };

describe("dashboards", () => {
  it("shows a loading message, then the courses", async () => {
    fakeBackend({ "GET /api/auth/me": [200, STUDENT], "GET /api/courses": [200, [COURSE]] });
    renderApp("/student", { loggedInAs: STUDENT });

    expect(await screen.findByText("Programming Fundamentals")).toBeInTheDocument();
    expect(screen.getByText("Ms. Khan", { selector: ".course-card .muted" })).toBeInTheDocument();
  });

  it("explains what to do when a student has no courses", async () => {
    fakeBackend({ "GET /api/auth/me": [200, STUDENT], "GET /api/courses": [200, []] });
    renderApp("/student", { loggedInAs: STUDENT });

    expect(await screen.findByText("You haven't joined any courses yet.")).toBeInTheDocument();
    expect(screen.getByText("Ask your teacher for a join code.")).toBeInTheDocument();
  });

  it("explains what to do when a teacher has no courses", async () => {
    fakeBackend({ "GET /api/auth/me": [200, TEACHER], "GET /api/courses": [200, []] });
    renderApp("/teacher", { loggedInAs: TEACHER });

    expect(await screen.findByText("You haven't created any courses yet.")).toBeInTheDocument();
  });

  it("shows an error with a Try again button that reloads", async () => {
    let calls = 0;
    fakeBackend({
      "GET /api/auth/me": [200, STUDENT],
      "GET /api/courses": () => {
        calls += 1;
        return calls === 1 ? [500, {}] : [200, [COURSE]];
      },
    });
    renderApp("/student", { loggedInAs: STUDENT });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on the server");
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Programming Fundamentals")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
