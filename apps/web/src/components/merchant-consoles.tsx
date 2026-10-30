/** Merchant console sections: readiness, staging, reporting, demo plan. */
"use client";

import { useEffect, useState } from "react";
import { VARIANTS } from "../lib/fixture/demo-catalog";
import { formatStamp } from "../lib/format";
import { sharedTransport } from "../lib/fixture/transport";
import type { components } from "../../../../contracts/runtime/client";

type CapabilityState = components["schemas"]["CapabilityState"];
type CatalogStage = components["schemas"]["CatalogStage"];
type InsightMetric = components["schemas"]["InsightMetric"];

export function MerchantConsoles({
  initialCapabilities = [],
  initialMetrics = [],
}: {
  initialCapabilities?: CapabilityState[];
  initialMetrics?: InsightMetric[];
}) {
  const [capabilities, setCapabilities] = useState<CapabilityState[]>(initialCapabilities);
  const [stage, setStage] = useState<CatalogStage | null>(null);
  const [metrics, setMetrics] = useState<InsightMetric[]>(initialMetrics);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCapabilities(sharedTransport().listCapabilities().data?.items ?? []);
    setMetrics(sharedTransport().getInsights().data?.metrics ?? []);
  }, []);

  function onStage() {
    setError(null);
    const result = sharedTransport().stageCatalog({
      sourceId: "demo-source",
      sourceVersion: "2026-10-30T00:00:00Z",
      variants: [...structuredClone(VARIANTS), structuredClone(VARIANTS[0])],
    });
    if (result.data) setStage(result.data);
    else setError(result.error?.error.message ?? "Staging failed.");
  }

  function onPublish() {
    setError(null);
    if (!stage) return;
    const result = sharedTransport().publishCatalog(stage.stageId, {
      approvePublication: true,
      expectedSourceVersion: stage.sourceVersion,
    });
    if (result.data) setMessage("Publication approved. Staging never publishes without explicit approval.");
    else setError(result.error?.error.message ?? "Publish failed.");
  }

  return (
    <>
      <section className="card" aria-label="Capability readiness">
        <h2>Capability readiness</h2>
        <ul className="item-list">
          {capabilities.map((c) => (
            <li key={c.capability}>
              <div className="item-row">
                <span>{c.capability.replaceAll("_", " ").toLowerCase()}</span>
                <span>
                  {c.state === "VERIFIED" ? (
                    <span className="chip chip--ok">verified</span>
                  ) : (
                    <span className="chip chip--warn">{c.state.replaceAll("_", " ").toLowerCase()} — live previews unavailable</span>
                  )}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" aria-label="Catalog staging">
        <h2>Catalog staging</h2>
        <p className="footnote">
          Staging diffs a source batch against the published catalog and reports errors. Publication
          is a separate, explicit approval — staging alone never changes the storefront.
        </p>
        <button type="button" className="button" onClick={onStage}>
          Stage demo batch
        </button>
        {stage ? (
          <div role="status">
            <p>
              Stage {stage.stageId.slice(0, 8)} · {stage.changedVariantIds.length} variants · source{" "}
              {stage.sourceVersion}
            </p>
            {stage.errors.length > 0 ? (
              <ul>
                {stage.errors.map((e) => (
                  <li key={e.code + e.message} className="footnote">
                    <span className="chip chip--bad">{e.code}</span> {e.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="footnote">No staging errors.</p>
            )}
            <button type="button" className="button" onClick={onPublish}>
              Approve publication
            </button>
          </div>
        ) : null}
      </section>

      <section className="card" aria-label="Reporting">
        <h2>Reporting</h2>
        <ul className="item-list">
          {metrics.map((m) => (
            <li key={m.name}>
              <div className="item-row">
                <span>{m.name.replace(/_/g, " ")}</span>
                <span>
                  <span className="chip">{m.mode}</span>{" "}
                  {m.suppressed ? (
                    <span className="chip chip--warn">suppressed — fewer than ten shoppers</span>
                  ) : (
                    <>
                      {m.numerator}
                      {m.denominator !== null ? ` / ${m.denominator}` : ""} shoppers
                    </>
                  )}
                  <span className="footnote">
                    {" "}
                    {formatStamp(m.windowStart)} – {formatStamp(m.windowEnd)}
                  </span>
                </span>
              </div>
            </li>
          ))}
        </ul>
        <p className="footnote">
          Aggregate metrics only — never another partner&apos;s private data. Demo revenue is
          excluded from real revenue and no demo revenue is claimed.
        </p>
      </section>

      <section className="card" aria-label="Demo plan">
        <h2>Demo plan</h2>
        <p className="footnote">
          Plan: Demo — INR 0, no real invoice collection. The allowance is a configured provider-unit
          cap; overage never auto-charges, it blocks new paid calls until an admin changes the
          authorized cap.
        </p>
      </section>

      {message ? (
        <p role="status" className="mode-note">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="error-note" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

