"use client";

/** Route-level error boundary. Shows the sanitized cause; never invents one. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <>
      <h1>Something went wrong</h1>
      <p className="error-note" role="alert">
        The screen failed to load. Nothing was submitted.{" "}
        {error.digest ? <span>(Reference {error.digest})</span> : null}
      </p>
      <button type="button" className="button" onClick={reset}>
        Try again
      </button>
    </>
  );
}
