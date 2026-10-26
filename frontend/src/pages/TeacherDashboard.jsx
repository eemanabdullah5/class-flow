import { api } from "../api/client.js";
import CourseList from "../components/CourseList.jsx";
import CreateCourseForm from "../components/CreateCourseForm.jsx";
import useApi from "../hooks/useApi.js";

export default function TeacherDashboard() {
  const { data: courses, loading, error, reload } = useApi(() => api.get("/api/courses"));

  return (
    <main className="page stack">
      <h1>Courses I teach</h1>
      <CourseList
        courses={courses}
        loading={loading}
        error={error}
        onRetry={reload}
        showJoinCode
        emptyTitle="You haven't created any courses yet."
        emptyMessage="Create your first course below to get a join code for your students."
      />
      <CreateCourseForm onCreated={reload} />
    </main>
  );
}
