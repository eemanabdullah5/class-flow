import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import StudentWorkPanel from "../components/StudentWorkPanel.jsx";
import useApi from "../hooks/useApi.js";
import { formatDateTime } from "../utils/dates.js";

// Shared by students and teachers. Students get their own "Your work" panel;
// the teacher's grading view is added in step 6.4.
export default function AssignmentPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const { data: assignment, loading, error, reload } = useApi(
    () => api.get(`/api/assignments/${assignmentId}`),
    [assignmentId],
  );

  if (loading && !assignment) {
    return (
      <main className="page">
        <Loading label="Loading assignment…" />
      </main>
    );
  }
  if (error) {
    return (
      <main className="page stack">
        <Link to="/" className="back-link">
          ← My courses
        </Link>
        <ErrorMessage message={error} onRetry={reload} />
      </main>
    );
  }

  return (
    <main className="page stack">
      <Link to={`/courses/${assignment.course_id}`} className="back-link">
        ← Back to course
      </Link>

      <header className="card">
        <h1>{assignment.title}</h1>
        <p className="muted">
          Due {formatDateTime(assignment.due_at)} · {assignment.max_points} points
        </p>
        {assignment.instructions && <p className="instructions">{assignment.instructions}</p>}
      </header>

      {user.role === "student" ? (
        <StudentWorkPanel assignment={assignment} />
      ) : (
        <p className="muted">The grading view for teachers is coming in the next step.</p>
      )}
    </main>
  );
}
