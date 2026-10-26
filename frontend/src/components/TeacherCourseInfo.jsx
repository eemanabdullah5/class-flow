import { useState } from "react";

import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import EmptyState from "./EmptyState.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";

/** The join code, big enough to read out in class, with a Copy button. */
export function JoinCodeBox({ code }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false); // some browsers block the clipboard; the code is still visible
    }
  }

  return (
    <div className="card join-code-box">
      <span className="muted">Join code</span>
      <span className="join-code">{code}</span>
      <button type="button" className="button button-secondary" onClick={copy}>
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}

/** Everyone who has joined the course. */
export function Roster({ courseId }) {
  const { data: students, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}/students`),
    [courseId],
  );

  if (loading && !students) return <Loading label="Loading students…" />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (students.length === 0) {
    return <EmptyState title="No students yet." message="Share the join code so students can join." />;
  }

  return (
    <ul className="roster">
      {students.map((student) => (
        <li key={student.id}>
          <span>{student.full_name}</span>
          <span className="muted small">{student.email}</span>
        </li>
      ))}
    </ul>
  );
}
