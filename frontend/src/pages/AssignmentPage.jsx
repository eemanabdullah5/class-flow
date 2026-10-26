import { useState } from "react";
import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import AssignmentForm from "../components/AssignmentForm.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import StudentWorkPanel from "../components/StudentWorkPanel.jsx";
import TeacherGradingPanel from "../components/TeacherGradingPanel.jsx";
import useApi from "../hooks/useApi.js";
import { formatDateTime } from "../utils/dates.js";

// Shared by students and teachers. Students get their own "Your work" panel;
// teachers can edit the assignment and grade every student.
export default function AssignmentPage() {
  const { assignmentId } = useParams();
  const { user } = useAuth();
  const [editing, setEditing] = useState(false);
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

  const isTeacher = user.role === "teacher";

  return (
    <main className="page stack">
      <Link to={`/courses/${assignment.course_id}`} className="back-link">
        ← Back to course
      </Link>

      {editing ? (
        <AssignmentForm
          existing={assignment}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <header className="card">
          <div className="work-header">
            <h1>{assignment.title}</h1>
            {isTeacher && (
              <button type="button" className="button button-secondary" onClick={() => setEditing(true)}>
                Edit
              </button>
            )}
          </div>
          <p className="muted">
            Due {formatDateTime(assignment.due_at)} · {assignment.max_points} points
          </p>
          {assignment.instructions && <p className="instructions">{assignment.instructions}</p>}
        </header>
      )}

      {isTeacher ? <TeacherGradingPanel assignment={assignment} /> : <StudentWorkPanel assignment={assignment} />}
    </main>
  );
}
