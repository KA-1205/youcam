import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1>We couldn&#39;t find that page</h1>
      <p>The link may be outdated, or the session it pointed at may have expired.</p>
      <p>
        <Link href="/">Back to the start</Link>
      </p>
    </>
  );
}
