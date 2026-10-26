import { useEffect } from "react";

/**
 * Set the browser tab's title, e.g. "Programming Fundamentals · ClassFlow".
 * Helps people with many tabs open, and screen readers announce it on each page.
 */
export default function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · ClassFlow` : "ClassFlow";
  }, [title]);
}
