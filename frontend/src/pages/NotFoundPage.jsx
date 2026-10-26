import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <main className="page">
      <div className="card">
        <h1>Page not found</h1>
        <p className="muted">The page you're looking for doesn't exist or was moved.</p>
        <Link to="/">Go to my dashboard</Link>
      </div>
    </main>
  );
}
