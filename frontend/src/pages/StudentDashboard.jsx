import { api } from "../api/client.js";
import CourseList from "../components/CourseList.jsx";
import JoinCourseForm from "../components/JoinCourseForm.jsx";
import useApi from "../hooks/useApi.js";

export default function StudentDashboard() {
  const { data: courses, loading, error, reload } = useApi(() => api.get("/api/courses"));

  return (
    <main className="page stack">
      <h1>My courses</h1>
      <JoinCourseForm onJoined={reload} />
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
