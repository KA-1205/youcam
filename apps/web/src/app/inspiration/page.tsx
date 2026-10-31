"use client";

import { InspirationSearch, GuidedEntry } from "../../components/inspiration";

export default function InspirationPage() {
  return (
    <>
      <h1>Inspiration</h1>
      <p className="lede">
        Start from a prompt, or search the authorized catalog. Everything routes into the same
        validated flows.
      </p>
      <GuidedEntry />
      <InspirationSearch />
    </>
  );
}
