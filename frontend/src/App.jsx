import { Navigate, Route, Routes } from "react-router";

import { useAuth } from "./auth/AuthContext.jsx";
import NavBar from "./components/NavBar.jsx";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

export default function App() {
  const { user, checking } = useAuth();

  // While a saved token is being checked, don't flash the login page.
  if (checking) {
    return <p className="page muted">Loading…</p>;
  }

  // Simple guards for now; step 6.2 replaces them with a reusable ProtectedRoute.
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <RegisterPage />} />
        <Route path="/" element={user ? <HomePage /> : <Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
