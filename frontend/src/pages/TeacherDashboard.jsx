import { api } from "../api/client.js";
import CourseList from "../components/CourseList.jsx";
import useApi from "../hooks/useApi.js";

// Step 6.4 adds the "Create course" form and links into each course.
export default function TeacherDashboard() {
  const { data: courses, loading, error, reload } = useApi(() => api.get("/api/courses"));

  return (
    <main className="page">
      <h1>Courses I teach</h1>
      <CourseList
        courses={courses}
        loading={loading}
        error={error}
        onRetry={reload}
        emptyTitle="You haven't created any courses yet."
        emptyMessage="Create your first course to get a join code for your students."
      />
    </main>
  );
}
