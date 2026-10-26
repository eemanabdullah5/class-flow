// The same upload rules as the backend, checked first so students get instant feedback.
// The backend checks again (including the file's real contents), so this is only for convenience.

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MB
export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".zip", ".png", ".jpg", ".jpeg"];
export const ACCEPT_ATTRIBUTE = ALLOWED_EXTENSIONS.join(",");

/** Returns an error message, or "" if the file looks fine. */
export function checkFile(file) {
  if (!file) return "Choose a file first.";
  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return "File type not allowed. Please upload a PDF, DOCX, ZIP, PNG or JPG file.";
  }
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_UPLOAD_BYTES) return "File is too large. The limit is 10 MB.";
  return "";
}

/** 2048 -> "2 KB" */
export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
