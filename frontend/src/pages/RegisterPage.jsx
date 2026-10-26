import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { useAuth } from "../auth/AuthContext.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import FormField from "../components/FormField.jsx";

// Same limits as the backend (bcrypt only uses the first 72 bytes).
const MIN_PASSWORD = 8;
const MAX_PASSWORD_BYTES = 72;

function validate({ fullName, email, password, confirmPassword }) {
  const problems = {};
  if (!fullName.trim()) problems.fullName = "Enter your full name.";
  if (!email.trim()) problems.email = "Enter your email.";
  else if (!/^\S+@\S+\.\S+$/.test(email.trim())) problems.email = "Enter a valid email address.";
  if (password.length < MIN_PASSWORD) {
    problems.password = `Password must be at least ${MIN_PASSWORD} characters.`;
  } else if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) {
    problems.password = "Password is too long.";
  }
  if (confirmPassword !== password) problems.confirmPassword = "Passwords don't match.";
  return problems;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ fullName: "", email: "", password: "", confirmPassword: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const problems = validate(form);
    setFieldErrors(problems);
    if (Object.keys(problems).length > 0) return;

    setSubmitting(true);
    try {
      await register({ fullName: form.fullName.trim(), email: form.email.trim(), password: form.password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Create a student account</h1>
        <p className="muted">Teacher accounts are created by the school administrator.</p>
        <ErrorMessage message={error} />

        <FormField
          id="fullName"
          label="Full name"
          autoComplete="name"
          value={form.fullName}
          onChange={update("fullName")}
          error={fieldErrors.fullName}
        />
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={update("email")}
          error={fieldErrors.email}
        />
        <FormField
          id="password"
          label="Password (at least 8 characters)"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={update("password")}
          error={fieldErrors.password}
        />
        <FormField
          id="confirmPassword"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={update("confirmPassword")}
          error={fieldErrors.confirmPassword}
        />

        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
        <p className="muted">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </main>
  );
}
