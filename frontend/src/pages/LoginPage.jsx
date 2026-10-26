import { useState } from "react";
import { Link } from "react-router";

import { useAuth } from "../auth/AuthContext.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import FormField from "../components/FormField.jsx";

export default function LoginPage() {
  const { login, notice } = useAuth(); // notice: e.g. "Your session has expired..."

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    // Quick checks for instant feedback. The backend checks again.
    const problems = {};
    if (!email.trim()) problems.email = "Enter your email.";
    if (!password) problems.password = "Enter your password.";
    setFieldErrors(problems);
    if (Object.keys(problems).length > 0) return;

    setSubmitting(true);
    try {
      // Once logged in, GuestRoute sends the user to their dashboard
      // (or back to the page they were trying to open).
      await login(email.trim(), password);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Log in</h1>
        {notice && !error && <div className="alert alert-info">{notice}</div>}
        <ErrorMessage message={error} />

        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
        />

        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Logging in…" : "Log in"}
        </button>
        <p className="muted">
          New student? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </main>
  );
}
