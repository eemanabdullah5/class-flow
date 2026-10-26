import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { StudentAssignments, TeacherAssignments } from "../components/CourseAssignments.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import MyResultCard from "../components/MyResultCard.jsx";
import { JoinCodeBox, Roster } from "../components/TeacherCourseInfo.jsx";
import useApi from "../hooks/useApi.js";
import useDocumentTitle from "../hooks/useDocumentTitle.js";

// Shared by students and teachers; each sees their own version of the assignment list.
export default function CoursePage() {
  const { courseId } = useParams();
  const { user } = useAuth();
  const { data: course, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}`),
    [courseId],
  );
  useDocumentTitle(course?.title);

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

          <Link to={`/courses/${courseId}/topics`} className="item-row">
            <span className="item-main">
              <span className="item-title">Topics and study order</span>
              <span className="muted">
                {user.role === "student"
                  ? "See what's covered and what to learn first."
                  : "Organize the course into topics and set what to learn first."}
              </span>
            </span>
            <span aria-hidden="true">→</span>
          </Link>

          {user.role === "teacher" && (
            <Link to={`/courses/${courseId}/results`} className="item-row">
              <span className="item-main">
                <span className="item-title">Results and reports</span>
                <span className="muted">Weighted results, letter grades, class statistics and the three reports.</span>
              </span>
              <span aria-hidden="true">→</span>
            </Link>
          )}

          {user.role === "student" ? (
            <>
              <MyResultCard courseId={courseId} />
              <h2>Assignments</h2>
              <StudentAssignments courseId={courseId} />
            </>
          ) : (
            <>
              <JoinCodeBox code={course.join_code} />
              <h2>Assignments</h2>
              <TeacherAssignments courseId={courseId} />
              <h2>Students</h2>
              <Roster courseId={courseId} />
            </>
          )}
        </>
      )}
    </main>
  );
}
