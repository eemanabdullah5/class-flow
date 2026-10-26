import { useState } from "react";

import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import { formatDateTime } from "../utils/dates.js";
import EmptyState from "./EmptyState.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";
import StatusBadge, { workStatus } from "./StatusBadge.jsx";

/** One student's row: their status, their file, and a grade form. */
function GradeRow({ row, assignment, onSaved }) {
  const { student, submission, grade } = row;
  const [score, setScore] = useState(grade ? String(grade.score) : "");
  const [feedback, setFeedback] = useState(grade?.feedback ?? "");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSave(event) {
    event.preventDefault();
    setError("");
    setSaved(false);
    const value = Number(score);
    if (score === "" || Number.isNaN(value) || value < 0 || value > assignment.max_points) {
      setError(`Enter a score from 0 to ${assignment.max_points}.`);
      return;
    }

    setSaving(true);
    try {
      await api.put(`/api/assignments/${assignment.id}/grades/${student.id}`, {
        score: value,
        feedback: feedback.trim() || null,
      });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload() {
    setError("");
    try {
      await api.download(`/api/submissions/${submission.id}/file`, submission.original_filename);
    } catch (err) {
      setError(err.message);
    }
  }

  const scoreId = `score-${student.id}`;
  const feedbackId = `feedback-${student.id}`;

  return (
    <li className="grade-row">
      <div className="grade-row-head">
        <span>
          <strong>{student.full_name}</strong>
          <br />
          <span className="muted small">{student.email}</span>
        </span>
        <StatusBadge
          submissionStatus={row.status === "missing" ? "none" : row.status}
          isLate={submission?.is_late}
          grade={grade}
          dueAt={assignment.due_at}
        />
      </div>

      {submission ? (
        <div className="file-row">
          <span>
            {submission.original_filename}
            <br />
            <span className="muted small">
              {submission.submitted_at
                ? `Turned in ${formatDateTime(submission.submitted_at)}`
                : "Draft, not turned in yet"}
            </span>
          </span>
          <button type="button" className="button button-secondary" onClick={handleDownload}>
            Download
          </button>
        </div>
      ) : (
        <p className="muted small">No file uploaded.</p>
      )}

      <form className="grade-form" onSubmit={handleSave} noValidate>
        <div className="field">
          <label htmlFor={scoreId}>Score (out of {assignment.max_points})</label>
          <input
            id={scoreId}
            type="number"
            min="0"
            max={assignment.max_points}
            step="any"
            value={score}
            onChange={(e) => setScore(e.target.value)}
          />
        </div>
        <div className="field grade-feedback-field">
          <label htmlFor={feedbackId}>Feedback (optional)</label>
          <input
            id={feedbackId}
            maxLength={2000}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
        </div>
        <button type="submit" className="button button-primary" disabled={saving}>
          {saving ? "Saving…" : grade ? "Update grade" : "Save grade"}
        </button>
      </form>
      <ErrorMessage message={error} />
      {saved && !error && (
        <p className="saved-note" role="status">
          Grade saved.
        </p>
      )}
    </li>
  );
}

/** Every enrolled student, including those who handed in nothing. */
export default function TeacherGradingPanel({ assignment }) {
  const { data: rows, loading, error, reload } = useApi(
    () => api.get(`/api/assignments/${assignment.id}/submissions`),
    [assignment.id],
  );

  if (loading && !rows) return <Loading label="Loading student work…" />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (rows.length === 0) {
    return <EmptyState title="No students in this course yet." message="Share the join code from the course page." />;
  }

  // A quick summary at the top: how many in each state.
  const counts = { turnedIn: 0, graded: 0, missing: 0 };
  for (const row of rows) {
    const { key } = workStatus({
      submissionStatus: row.status === "missing" ? "none" : row.status,
      isLate: row.submission?.is_late,
      grade: row.grade,
      dueAt: assignment.due_at,
    });
    if (key === "graded") counts.graded += 1;
    if (key === "submitted" || key === "late") counts.turnedIn += 1;
    if (key === "missing") counts.missing += 1;
  }

  return (
    <section className="stack" aria-labelledby="student-work">
      <h2 id="student-work">Student work</h2>
      <p className="muted">
        {rows.length} students · {counts.turnedIn} turned in, waiting for a grade · {counts.graded} graded ·{" "}
        {counts.missing} missing
      </p>
      <ul className="grade-list">
        {rows.map((row) => (
          <GradeRow key={row.student.id} row={row} assignment={assignment} onSaved={reload} />
        ))}
      </ul>
    </section>
  );
}
