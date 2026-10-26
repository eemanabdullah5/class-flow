import { useState } from "react";

import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import ErrorMessage from "./ErrorMessage.jsx";

function scoreText(score) {
  return score === null ? "no grade" : String(score);
}

/** "Sara Ahmed: 18 → no grade", naming the assignment if it isn't the one on this page. */
export function describeUndo(change, assignmentId) {
  const where = change.assignment_id === assignmentId ? "" : ` on ${change.assignment_title}`;
  return `${change.student_name}${where}: ${scoreText(change.from_score)} → ${scoreText(change.to_score)}`;
}

/**
 * Undo the teacher's newest grade change (from any of their assignments).
 * gradeVersion: goes up whenever a grade is saved, so the preview loads again.
 * onUndone(): called after an undo, so the student list can load again.
 */
export default function UndoGradeButton({ assignmentId, gradeVersion, onUndone }) {
  const { data: preview, loading, error, reload } = useApi(() => api.get("/api/grades/undo"), [gradeVersion]);
  const [undoing, setUndoing] = useState(false);
  const [undoError, setUndoError] = useState("");
  const [undone, setUndone] = useState(null);

  async function handleUndo() {
    setUndoError("");
    setUndone(null);
    setUndoing(true);
    try {
      setUndone(await api.post("/api/grades/undo"));
      onUndone();
    } catch (err) {
      setUndoError(err.message);
    } finally {
      setUndoing(false);
      reload(); // the next change down is now on top (or the stack is empty)
    }
  }

  return (
    <div className="undo-bar">
      <div className="undo-bar-row">
        <button
          type="button"
          className="button button-secondary"
          onClick={handleUndo}
          disabled={!preview || loading || undoing}
        >
          {undoing ? "Undoing…" : "Undo last grade change"}
        </button>
        {preview && <span>{describeUndo(preview, assignmentId)}</span>}
        {!preview && !loading && !error && <span className="muted">No grade changes to undo.</span>}
      </div>
      <ErrorMessage message={error} onRetry={reload} />
      <ErrorMessage message={undoError} />
      {undone && !undoError && (
        <p className="saved-note" role="status">
          Undone: {describeUndo(undone, assignmentId)}
        </p>
      )}
    </div>
  );
}
