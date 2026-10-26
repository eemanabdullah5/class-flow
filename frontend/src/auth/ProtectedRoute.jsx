import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "./AuthContext.jsx";

/** Where each role's home page is. */
export function dashboardPath(user) {
  return user.role === "teacher" ? "/teacher" : "/student";
}

/**
 * Wraps pages that need a logged-in user, and optionally a specific role.
 *
 * This only makes the app pleasant to use (no blank pages, no wrong menus).
 * The real protection is the backend, which checks every request again.
 */
export default function ProtectedRoute({ role }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    // Remember where they were going, so login can send them back there.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (role && user.role !== role) {
    return <Navigate to={dashboardPath(user)} replace />;
  }
  return <Outlet />; // show the page inside this route
}

/** For the login and register pages: logged-in users are sent on to the app. */
export function GuestRoute() {
  const { user } = useAuth();
  const location = useLocation();

  if (user) {
    return <Navigate to={location.state?.from || dashboardPath(user)} replace />;
  }
  return <Outlet />;
}

/** The "/" page: send each user to their own dashboard. */
export function RoleHome() {
  const { user } = useAuth();
  return <Navigate to={dashboardPath(user)} replace />;
}
