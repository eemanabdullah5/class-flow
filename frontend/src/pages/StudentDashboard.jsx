import { api } from "../api/client.js";
import CourseList from "../components/CourseList.jsx";
import useApi from "../hooks/useApi.js";

// Step 6.3 adds the "Join a course" box and links into each course.
export default function StudentDashboard() {
  const { data: courses, loading, error, reload } = useApi(() => api.get("/api/courses"));

  return (
    <main className="page">
      <h1>My courses</h1>
      <CourseList
        courses={courses}
        loading={loading}
        error={error}
        onRetry={reload}
        emptyTitle="You haven't joined any courses yet."
        emptyMessage="Ask your teacher for a join code."
      />
    </main>
  );
}
