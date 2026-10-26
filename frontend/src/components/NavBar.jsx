import { Link } from "react-router";

import { useAuth } from "../auth/AuthContext.jsx";

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <Link to="/" className="brand">
        ClassFlow
      </Link>
      {user && (
        <div className="navbar-user">
          <span>
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
