import { useState } from "react";
import { Link } from "react-router";

import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import { formatDateTime } from "../utils/dates.js";
import AssignmentForm from "./AssignmentForm.jsx";
import EmptyState from "./EmptyState.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";
import StatusBadge from "./StatusBadge.jsx";

/** Students: every assignment with their own status, in one request (/my-work). */
export function StudentAssignments({ courseId }) {
  const { data: rows, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}/my-work`),
    [courseId],
  );

  if (loading && !rows) return <Loading label="Loading assignments…" />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;
  if (rows.length === 0) {
    return <EmptyState title="No assignments yet." message="Your teacher hasn't posted any work." />;
  }

  return (
    <ul className="item-list">
      {rows.map(({ assignment, submission_status, is_late, grade }) => (
        <li key={assignment.id}>
          <Link to={`/assignments/${assignment.id}`} className="item-row">
            <span className="item-main">
              <span className="item-title">{assignment.title}</span>
              <span className="muted">Due {formatDateTime(assignment.due_at)}</span>
            </span>
            <span className="item-side">
              {grade && (
                <span className="score">
                  {grade.score}/{assignment.max_points}
                </span>
              )}
              <StatusBadge
                submissionStatus={submission_status}
                isLate={is_late}
                grade={grade}
                dueAt={assignment.due_at}
              />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Teachers: the assignment list plus a "New assignment" form. */
export function TeacherAssignments({ courseId }) {
  const [creating, setCreating] = useState(false);
  const { data: assignments, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}/assignments`),
    [courseId],
  );

  function handleCreated() {
    setCreating(false);
    reload();
  }

  return (
    <div className="stack">
      {creating ? (
        <AssignmentForm courseId={courseId} onSaved={handleCreated} onCancel={() => setCreating(false)} />
      ) : (
        <div>
          <button type="button" className="button button-primary" onClick={() => setCreating(true)}>
            + New assignment
          </button>
        </div>
      )}

      {loading && !assignments && <Loading label="Loading assignments…" />}
      <ErrorMessage message={error} onRetry={reload} />
      {assignments && assignments.length === 0 && (
        <EmptyState title="No assignments yet." message="Create one so your students have something to work on." />
      )}
      {assignments && assignments.length > 0 && (
        <ul className="item-list">
          {assignments.map((assignment) => (
            <li key={assignment.id}>
              <Link to={`/assignments/${assignment.id}`} className="item-row">
                <span className="item-main">
                  <span className="item-title">{assignment.title}</span>
                  <span className="muted">Due {formatDateTime(assignment.due_at)}</span>
                </span>
                <span className="muted">{assignment.max_points} points</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
