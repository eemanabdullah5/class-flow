import { Link } from "react-router";

import EmptyState from "./EmptyState.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";

// The three states every list has: loading, error, empty, and then the actual list.
// showJoinCode: teachers see each course's code on its card.
export default function CourseList({ courses, loading, error, onRetry, emptyTitle, emptyMessage, showJoinCode = false }) {
  if (loading && !courses) return <Loading label="Loading courses…" />;
  if (error) return <ErrorMessage message={error} onRetry={onRetry} />;
  if (courses.length === 0) return <EmptyState title={emptyTitle} message={emptyMessage} />;

  return (
    <ul className="course-grid">
      {courses.map((course) => (
        <li key={course.id}>
          <Link to={`/courses/${course.id}`} className="course-card">
            <span className="course-title">{course.title}</span>
            <span className="muted">{course.teacher_name}</span>
            {showJoinCode && <span className="muted small">Join code: {course.join_code}</span>}
          </Link>
        </li>
      ))}
    </ul>
  );
}
