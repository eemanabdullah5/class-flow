import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { tokenStorage } from "../api/client.js";
import { AuthProvider } from "../auth/AuthContext.jsx";
import LoginPage from "../pages/LoginPage.jsx";

function showLoginPage(initialState) {
  render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state: initialState }]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<p>Home page</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

function fakeFetch(status, body) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function fillIn(email, password) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Log in" }));
}

describe("LoginPage", () => {
  it("asks for both fields before sending anything", async () => {
    const fetchMock = fakeFetch(200, {});
    showLoginPage();

    await userEvent.setup().click(screen.getByRole("button", { name: "Log in" }));

    expect(screen.getByText("Enter your email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the backend's message for a wrong password", async () => {
    fakeFetch(401, { detail: "Invalid email or password." });
    showLoginPage();

    await fillIn("sara@uni.edu", "wrongpass1");

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(tokenStorage.get()).toBeNull();
  });

  it("saves the token and goes to the home page after logging in", async () => {
    fakeFetch(200, {
      access_token: "new.token.value",
      token_type: "bearer",
      user: { id: 1, email: "sara@uni.edu", full_name: "Sara Ahmed", role: "student" },
    });
    showLoginPage();

    await fillIn("sara@uni.edu", "mypassword1");

    expect(await screen.findByText("Home page")).toBeInTheDocument();
    expect(tokenStorage.get()).toBe("new.token.value");
  });

  it("shows why the user was sent to the login page", () => {
    fakeFetch(200, {});
    showLoginPage({ notice: "Your session has expired. Please log in again." });

    expect(screen.getByText("Your session has expired. Please log in again.")).toBeInTheDocument();
  });
});
