// A labelled input with an optional error message underneath.
// The label is linked to the input, so clicking it focuses the field
// and screen readers read them together.
// Pass multiline for a bigger text box (e.g. instructions or feedback).
export default function FormField({ id, label, error, multiline = false, ...inputProps }) {
  const errorId = `${id}-error`;
  const Input = multiline ? "textarea" : "input";
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <Input
        id={id}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {error && (
        <p id={errorId} className="field-error">
          {error}
        </p>
      )}
    </div>
  );
}
