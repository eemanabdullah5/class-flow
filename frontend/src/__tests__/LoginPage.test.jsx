import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { tokenStorage } from "../api/client.js";
import { STUDENT, fakeBackend, renderApp } from "./helpers.jsx";

async function fillIn(email, password) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Log in" }));
}

describe("LoginPage", () => {
  it("asks for both fields before sending anything", async () => {
    const fetchMock = fakeBackend({});
    renderApp("/login");

    await userEvent.setup().click(screen.getByRole("button", { name: "Log in" }));

    expect(screen.getByText("Enter your email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the backend's message for a wrong password", async () => {
    fakeBackend({ "POST /api/auth/login": [401, { detail: "Invalid email or password." }] });
    renderApp("/login");

    await fillIn("sara@uni.edu", "wrongpass1");

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(tokenStorage.get()).toBeNull();
  });

  it("saves the token and opens the dashboard after logging in", async () => {
    fakeBackend({
      "POST /api/auth/login": [200, { access_token: "new.token.value", token_type: "bearer", user: STUDENT }],
      "GET /api/courses": [200, []],
    });
    renderApp("/login");

    await fillIn(STUDENT.email, "mypassword1");

    expect(await screen.findByRole("heading", { name: "My courses" })).toBeInTheDocument();
    expect(tokenStorage.get()).toBe("new.token.value");
  });
});
