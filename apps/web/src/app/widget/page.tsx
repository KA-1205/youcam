import { Suspense } from "react";
import { WidgetCard } from "../../components/widget-card";

export default function WidgetPage() {
  return (
    <main style={{ maxWidth: "28rem", margin: "3rem auto" }}>
      <Suspense fallback={<p className="loading-note">Loading…</p>}>
        <WidgetCard />
      </Suspense>
    </main>
  );
}
