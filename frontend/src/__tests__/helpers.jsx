// Shared helpers for frontend tests (this file has no tests itself).
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import App from "../App.jsx";
import { tokenStorage } from "../api/client.js";
import { AuthProvider } from "../auth/AuthContext.jsx";

export const STUDENT = { id: 2, email: "student1@example.com", full_name: "Sara Ahmed", role: "student" };
export const TEACHER = { id: 1, email: "teacher@example.com", full_name: "Ms. Khan", role: "teacher" };

/**
 * Replace fetch with a pretend backend.
 *   fakeBackend({ "GET /api/courses": [200, []] })
 * A value can also be a function, to answer differently on each call.
 * Anything not listed answers 404.
 */
export function fakeBackend(routes) {
  const fetchMock = vi.fn(async (path, options = {}) => {
    const route = routes[`${options.method || "GET"} ${path}`];
    const [status, body] = typeof route === "function" ? route(options) : route || [404, { detail: "Not found" }];
    return new Response(JSON.stringify(body), { status });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Draw the whole app at a URL. Pass a user to start logged in as them. */
export function renderApp(path, { loggedInAs } = {}) {
  if (loggedInAs) tokenStorage.set("pretend.login.token");
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}
