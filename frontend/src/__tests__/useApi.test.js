import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import useApi from "../hooks/useApi.js";

describe("useApi", () => {
  it("starts loading, then gives the data", async () => {
    const { result } = renderHook(() => useApi(() => Promise.resolve(["a", "b"])));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["a", "b"]);
    expect(result.current.error).toBe("");
  });

  it("gives the error message when loading fails", async () => {
    const { result } = renderHook(() => useApi(() => Promise.reject(new Error("Course not found."))));

    await waitFor(() => expect(result.current.error).toBe("Course not found."));
    expect(result.current.data).toBeNull();
  });

  it("loads again when reload() is called", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(1).mockResolvedValueOnce(2);
    const { result } = renderHook(() => useApi(fetcher));
    await waitFor(() => expect(result.current.data).toBe(1));

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.data).toBe(2));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("loads again when a dependency changes", async () => {
    const fetcher = vi.fn((id) => Promise.resolve(`course ${id}`));
    const { result, rerender } = renderHook(({ id }) => useApi(() => fetcher(id), [id]), {
      initialProps: { id: 1 },
    });
    await waitFor(() => expect(result.current.data).toBe("course 1"));

    rerender({ id: 2 });

    await waitFor(() => expect(result.current.data).toBe("course 2"));
  });
});
