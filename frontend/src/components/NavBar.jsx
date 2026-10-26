import { Link, NavLink } from "react-router";

import { useAuth } from "../auth/AuthContext.jsx";
import { dashboardPath } from "../auth/ProtectedRoute.jsx";

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      {/* Hidden until focused with Tab: lets keyboard users jump past the menu. */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <nav className="navbar-left" aria-label="Main">
        <Link to="/" className="brand">
          ClassFlow
        </Link>
        {user && (
          <NavLink to={dashboardPath(user)} className="nav-link">
            Dashboard
          </NavLink>
        )}
      </nav>
      {user && (
        <div className="navbar-user">
          <span className="navbar-name">
            {user.full_name} <span className="role-tag">{user.role}</span>
          </span>
          <button type="button" className="button button-secondary" onClick={logout}>
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
