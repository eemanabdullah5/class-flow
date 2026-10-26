import { afterEach, describe, expect, it, vi } from "vitest";

import { api, request, setUnauthorizedHandler, tokenStorage } from "../api/client.js";

// Replace the browser's fetch with a fake that returns the given status and JSON.
function fakeFetch(status, body) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => setUnauthorizedHandler(() => {}));

describe("api client", () => {
  it("sends the saved token in the Authorization header", async () => {
    tokenStorage.set("abc.def.ghi");
    const fetchMock = fakeFetch(200, { id: 1 });

    await api.get("/api/auth/me");

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer abc.def.ghi");
  });

  it("does not send a token for login requests", async () => {
    tokenStorage.set("old.token.value");
    const fetchMock = fakeFetch(200, {});

    await request("/api/auth/login", { method: "POST", body: {}, auth: false });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("returns the JSON body on success", async () => {
    fakeFetch(200, { status: "ok" });

    await expect(api.get("/api/health")).resolves.toEqual({ status: "ok" });
  });

  it("on 401 clears the token and calls the logout handler", async () => {
    tokenStorage.set("expired.token.value");
    fakeFetch(401, { detail: "Your session has expired. Please log in again." });
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    await expect(api.get("/api/courses")).rejects.toThrow("Your session has expired");

    expect(tokenStorage.get()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledWith("Your session has expired. Please log in again.");
  });

  it("does not treat a wrong password as an expired session", async () => {
    fakeFetch(401, { detail: "Invalid email or password." });
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    await expect(
      request("/api/auth/login", { method: "POST", body: {}, auth: false }),
    ).rejects.toThrow("Invalid email or password.");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("turns FastAPI validation errors into readable text", async () => {
    fakeFetch(422, {
      detail: [
        { loc: ["body", "full_name"], msg: "Value error, Full name cannot be blank." },
        { loc: ["body", "password"], msg: "String should have at least 8 characters" },
      ],
    });

    await expect(api.post("/api/auth/register", {})).rejects.toThrow(
      "Full name: Full name cannot be blank. Password: String should have at least 8 characters",
    );
  });

  it("gives a clear message when the server can't be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));

    await expect(api.get("/api/health")).rejects.toThrow("Can't reach the server");
  });
});
