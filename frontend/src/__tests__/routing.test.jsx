import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { tokenStorage } from "../api/client.js";
import { STUDENT, TEACHER, fakeBackend, renderApp } from "./helpers.jsx";

function backendFor(user) {
  return fakeBackend({
    "GET /api/auth/me": [200, user],
    "GET /api/courses": [200, []],
  });
}

describe("routing and protection", () => {
  it("sends logged-out visitors to the login page", async () => {
    fakeBackend({});
    renderApp("/teacher");

    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("sends a student from / to the student dashboard", async () => {
    backendFor(STUDENT);
    renderApp("/", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: "My courses" })).toBeInTheDocument();
  });

  it("sends a teacher from / to the teacher dashboard", async () => {
    backendFor(TEACHER);
    renderApp("/", { loggedInAs: TEACHER });

    expect(await screen.findByRole("heading", { name: "Courses I teach" })).toBeInTheDocument();
  });

  it("keeps a student out of the teacher pages", async () => {
    backendFor(STUDENT);
    renderApp("/teacher", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: "My courses" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Courses I teach" })).not.toBeInTheDocument();
  });

  it("keeps a teacher out of the student pages", async () => {
    backendFor(TEACHER);
    renderApp("/student", { loggedInAs: TEACHER });

    expect(await screen.findByRole("heading", { name: "Courses I teach" })).toBeInTheDocument();
  });

  it("sends logged-in users away from the login page", async () => {
    backendFor(STUDENT);
    renderApp("/login", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: "My courses" })).toBeInTheDocument();
  });

  it("shows Not Found for unknown pages", async () => {
    backendFor(STUDENT);
    renderApp("/no-such-page", { loggedInAs: STUDENT });

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("returns to the page the user wanted after logging in", async () => {
    fakeBackend({
      "POST /api/auth/login": [200, { access_token: "new.token", token_type: "bearer", user: TEACHER }],
      "GET /api/courses": [200, []],
    });
    renderApp("/teacher");
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Email"), TEACHER.email);
    await user.type(screen.getByLabelText("Password"), "demo-pass-123");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("heading", { name: "Courses I teach" })).toBeInTheDocument();
  });

  it("shows 'session expired' when a saved token no longer works", async () => {
    fakeBackend({
      "GET /api/auth/me": [401, { detail: "Your session has expired. Please log in again." }],
    });
    renderApp("/student", { loggedInAs: STUDENT });

    expect(await screen.findByText("Your session has expired. Please log in again.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(tokenStorage.get()).toBeNull();
  });

  it("logs out from the navbar", async () => {
    backendFor(STUDENT);
    renderApp("/student", { loggedInAs: STUDENT });

    await userEvent.setup().click(await screen.findByRole("button", { name: "Log out" }));

    expect(await screen.findByText("You have been logged out.")).toBeInTheDocument();
    expect(tokenStorage.get()).toBeNull();
  });

  it("names the browser tab after the page", async () => {
    backendFor(STUDENT);
    renderApp("/student", { loggedInAs: STUDENT });

    await screen.findByRole("heading", { name: "My courses" });
    expect(document.title).toBe("My courses · ClassFlow");
  });

  it("has a Dashboard link and a skip link for keyboard users", async () => {
    backendFor(TEACHER);
    renderApp("/no-such-page", { loggedInAs: TEACHER });

    expect(await screen.findByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/teacher");
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute("href", "#main-content");
  });
});
