// A red box for errors. role="alert" makes screen readers announce it.
export default function ErrorMessage({ message }) {
  if (!message) return null;
  return (
    <div className="alert alert-error" role="alert">
      {message}
    </div>
  );
}
