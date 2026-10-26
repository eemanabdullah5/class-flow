// Runs before every frontend test file.
import "@testing-library/jest-dom/vitest"; // adds checks like toBeInTheDocument()
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup(); // remove whatever the test drew on the page
  sessionStorage.clear(); // no login token leaks into the next test
  vi.unstubAllGlobals(); // undo any fake fetch
});
