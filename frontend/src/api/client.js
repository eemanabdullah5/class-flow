// The ONLY place in the frontend that talks to the backend.
// It adds the login token, turns error responses into readable messages,
// and reacts to 401 (expired or invalid login) in one place.

const TOKEN_KEY = "classflow_token";

// sessionStorage: kept while this tab is open, cleared when the tab closes.
// Wrapped in try/catch because some browsers block storage (e.g. private mode).
export const tokenStorage = {
  get() {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Without storage the user stays logged in until the page is refreshed.
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // nothing to clear
    }
  },
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// AuthContext replaces this with "log out and go to the login page".
let handleUnauthorized = () => {};
export function setUnauthorizedHandler(handler) {
  handleUnauthorized = handler;
}

// "full_name" -> "Full name"
function fieldLabel(field) {
  const text = field.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// FastAPI's 422 errors are a list like [{loc: ["body", "password"], msg: "..."}].
function validationMessage(error) {
  const field = (error.loc || []).filter((part) => part !== "body").join(" ");
  const message = String(error.msg || "is invalid").replace(/^Value error, /, "");
  return field ? `${fieldLabel(field)}: ${message}` : message;
}

function errorMessage(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(validationMessage).join(" ");
  if (status >= 500) return "Something went wrong on the server. Please try again.";
  return `Request failed (${status}).`;
}

/**
 * Send a request to the backend and return the JSON response.
 * Throws ApiError with a readable message if anything goes wrong.
 *
 * auth: false is used for login/register, so an old token is never sent
 * and a 401 there just means "wrong password", not "session expired".
 * asBlob: true returns the raw file instead of JSON (used for downloads).
 */
export async function request(path, { method = "GET", body, formData, auth = true, asBlob = false } = {}) {
  const headers = {};
  const token = auth ? tokenStorage.get() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (formData) {
    payload = formData; // the browser sets the right Content-Type for files
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new ApiError("Can't reach the server. Is the backend running?", 0);
  }

  if (response.ok && asBlob) return response.blob();

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (response.status === 401 && token) {
    tokenStorage.clear();
    handleUnauthorized(errorMessage(data, 401));
  }
  if (!response.ok) {
    throw new ApiError(errorMessage(data, response.status), response.status);
  }
  return data;
}

/**
 * Download a protected file and let the browser save it.
 * A plain <a href> link can't send our login token, so we fetch the file
 * ourselves (with the token) and then hand it to the browser.
 */
async function download(path, filename) {
  const blob = await request(path, { asBlob: true });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  delete: (path) => request(path, { method: "DELETE" }),
  upload: (path, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request(path, { method: "PUT", formData });
  },
  download,
};
