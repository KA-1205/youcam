"use client";

import { useEffect } from "react";
import { CompareBoard } from "../../components/compare-board";
import { useSession } from "../../lib/session-context";

export default function ComparePage() {
  const { state, actions } = useSession();
  const { looks } = state;

  useEffect(() => {
    actions.restore();
  }, []);

  return (
    <>
      <h1>Compare looks</h1>
      <p className="lede">
        Exact products and prices, aligned row by row. Owned items show zero new spend.
      </p>
      <CompareBoard looks={looks} />
    </>
  );
}
