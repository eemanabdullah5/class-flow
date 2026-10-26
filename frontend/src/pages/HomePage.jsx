import { useAuth } from "../auth/AuthContext.jsx";

// Temporary page for step 6.1. The real student and teacher dashboards replace it in 6.3 and 6.4.
export default function HomePage() {
  const { user } = useAuth();

  return (
    <main className="page">
      <div className="card">
        <h1>Welcome, {user.full_name}!</h1>
        <p>
          You are logged in as a <strong>{user.role}</strong> ({user.email}).
        </p>
        <p className="muted">Your dashboard is coming in the next steps.</p>
      </div>
    </main>
  );
}
