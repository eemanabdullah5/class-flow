import { Link } from "react-router";

import useDocumentTitle from "../hooks/useDocumentTitle.js";

export default function NotFoundPage() {
  useDocumentTitle("Page not found");
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
