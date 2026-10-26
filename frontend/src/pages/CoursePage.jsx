import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { StudentAssignments, TeacherAssignments } from "../components/CourseAssignments.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import useApi from "../hooks/useApi.js";

// Shared by students and teachers; each sees their own version of the assignment list.
export default function CoursePage() {
  const { courseId } = useParams();
  const { user } = useAuth();
  const { data: course, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}`),
    [courseId],
  );

  return (
    <main className="page stack">
      <Link to="/" className="back-link">
        ← My courses
      </Link>

      {loading && !course && <Loading label="Loading course…" />}
      <ErrorMessage message={error} onRetry={reload} />

      {course && (
        <>
          <header className="course-header">
            <h1>{course.title}</h1>
            <p>{course.teacher_name}</p>
            {course.description && <p className="course-description">{course.description}</p>}
          </header>

          <h2>Assignments</h2>
          {user.role === "student" ? (
            <StudentAssignments courseId={courseId} />
          ) : (
            <TeacherAssignments courseId={courseId} />
          )}
        </>
      )}
    </main>
  );
}
