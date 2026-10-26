import { Route, Routes } from "react-router";

import { useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute, { GuestRoute, RoleHome } from "./auth/ProtectedRoute.jsx";
import Loading from "./components/Loading.jsx";
import NavBar from "./components/NavBar.jsx";
import AssignmentPage from "./pages/AssignmentPage.jsx";
import CoursePage from "./pages/CoursePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import TeacherDashboard from "./pages/TeacherDashboard.jsx";
import TopicsPage from "./pages/TopicsPage.jsx";

export default function App() {
  const { checking } = useAuth();

  // While a saved token is being checked, don't flash the login page.
  if (checking) {
    return (
      <main className="page">
        <Loading />
      </main>
    );
  }

  return (
    <>
      <NavBar />
      {/* The "Skip to main content" link jumps here. */}
      <div id="main-content" tabIndex={-1}>
        <Routes>
          {/* Only for logged-out visitors */}
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Any logged-in user */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<RoleHome />} />
            {/* Shared pages: the backend decides what each person may see */}
            <Route path="/courses/:courseId" element={<CoursePage />} />
            <Route path="/courses/:courseId/topics" element={<TopicsPage />} />
            <Route path="/assignments/:assignmentId" element={<AssignmentPage />} />
          </Route>

          {/* Students only */}
          <Route element={<ProtectedRoute role="student" />}>
            <Route path="/student" element={<StudentDashboard />} />
          </Route>

          {/* Teachers only */}
          <Route element={<ProtectedRoute role="teacher" />}>
            <Route path="/teacher" element={<TeacherDashboard />} />
            <Route path="/courses/:courseId/results" element={<ResultsPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </div>
    </>
  );
}
