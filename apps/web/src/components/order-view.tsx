/** Demo order view: timeline, honest payment states and labelled operator controls. */
"use client";

import Link from "next/link";
import { useState } from "react";
import { formatMinor } from "../lib/format";
import { sharedTransport } from "../lib/fixture/transport";
import type { components } from "../../../../contracts/runtime/client";

type OrderSnapshot = components["schemas"]["OrderSnapshot"];

const TIMELINE = ["CREATED", "PAYMENT_PENDING", "PAID", "ALLOCATED", "PICKED", "SHIPPED", "DELIVERED"] as const;

const STATUS_COPY: Record<string, string> = {
  PAYMENT_PENDING: "Payment pending. If authentication is required, approve or reject the simulated step below.",
};

/**
 * Order view with a demo timeline. Cancel works before shipment; returns open
 * after delivery. Fulfilment transitions belong to the operator role and are
 * labelled as demo controls.
 */
export function OrderView({ order, paymentUnknown }: { order: OrderSnapshot; paymentUnknown: boolean }) {
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<OrderSnapshot>(order);

  const version = current.orderVersion;
  const status = current.status;

  function run(action: () => { data?: OrderSnapshot; error?: { error: { message: string } } }) {
    const result = action();
    if (result.data) setCurrent(result.data);
    else setError(result.error?.error.message ?? "That action failed.");
  }

  const reached = new Set<string>([...TIMELINE.slice(0, TIMELINE.indexOf(status as never) + 1)]);
  if (["CANCELLED", "REFUNDED"].includes(status)) reached.add(status);

  return (
    <>
      <p className="mode-note" role="status">
        DEMO order — simulated payment and simulated warehouse. No carrier location is invented and
        no money moves.
      </p>
      {paymentUnknown && status === "PAYMENT_PENDING" ? (
        <p role="status" className="mode-note">
          Checking demo payment — the outcome is not known yet. Reconcile below; the fixture
          guarantees no late success.
        </p>
      ) : null}
      <p className="lede">{STATUS_COPY[status] ?? `Order status: ${status.replaceAll("_", " ").toLowerCase()}.`}</p>
      {error ? (
        <p className="error-note" role="alert">
          {error}
        </p>
      ) : null}

      <section className="card" aria-label="Order timeline">
        <h2>Timeline</h2>
        <ol className="item-list">
          {TIMELINE.map((step) => (
            <li key={step}>
              {reached.has(step) ? "✓" : "·"} {step.replaceAll("_", " ").toLowerCase()}
            </li>
          ))}
          {status === "CANCELLED" ? <li>✓ cancelled</li> : null}
          {status === "REFUNDED" ? <li>✓ refunded</li> : null}
        </ol>
        {current.returnStatus !== "NONE" ? (
          <p>
            Return: {current.returnStatus.toLowerCase()}{" "}
            <span className="chip chip--warn">{current.returnStatus}</span>
          </p>
        ) : null}
        <p className="footnote">Total {formatMinor(current.totalMinor, current.currency)} · order v{version}</p>
      </section>

      <section className="card" aria-label="Order actions">
        <h2>Actions</h2>
        <div className="look-actions">
          {["CREATED", "PAYMENT_PENDING", "PAID", "ALLOCATED", "PICKED"].includes(status) ? (
            <button
              type="button"
              className="button button--danger"
              onClick={() => run(() => sharedTransport().cancelOrder(current.orderId, { expectedOrderVersion: version }))}
            >
              Cancel order
            </button>
          ) : null}
          {status === "PAYMENT_PENDING" ? (
            <>
              <button
                type="button"
                className="button"
                onClick={() => run(() => sharedTransport().approveDemoAuth(current.orderId))}
              >
                Approve simulated authentication
              </button>
              <button
                type="button"
                className="button button--secondary"
                onClick={() => run(() => sharedTransport().rejectDemoAuth(current.orderId))}
              >
                Reject authentication
              </button>
            </>
          ) : null}
          {paymentUnknown && status === "PAYMENT_PENDING" ? (
            <button
              type="button"
              className="button"
              onClick={() => run(() => sharedTransport().reconcileDemoTimeout(current.orderId))}
            >
              Reconcile demo timeout
            </button>
          ) : null}
          {status === "DELIVERED" && current.returnStatus === "NONE" ? (
            <button
              type="button"
              className="button"
              onClick={() => run(() => sharedTransport().requestReturn(current.orderId, { expectedOrderVersion: version }))}
            >
              Request return
            </button>
          ) : null}
        </div>
        <p className="footnote">
          Operator demo controls (fixtures only):{" "}
          {status === "ALLOCATED" ? (
            <button
              type="button"
              className="button button--secondary"
              onClick={() =>
                run(() => sharedTransport().advanceFulfilment(current.orderId, { expectedOrderVersion: version, nextStatus: "PICKED" }))
              }
            >
              Mark picked
            </button>
          ) : null}{" "}
          {status === "PICKED" ? (
            <button
              type="button"
              className="button button--secondary"
              onClick={() =>
                run(() => sharedTransport().advanceFulfilment(current.orderId, { expectedOrderVersion: version, nextStatus: "SHIPPED" }))
              }
            >
              Mark shipped
            </button>
          ) : null}{" "}
          {status === "SHIPPED" ? (
            <button
              type="button"
              className="button button--secondary"
              onClick={() =>
                run(() => sharedTransport().advanceFulfilment(current.orderId, { expectedOrderVersion: version, nextStatus: "DELIVERED" }))
              }
            >
              Mark delivered
            </button>
          ) : null}{" "}
          {current.returnStatus === "REQUESTED" ? (
            <button
              type="button"
              className="button button--secondary"
              onClick={() => run(() => sharedTransport().receiveReturn(current.orderId, { expectedOrderVersion: version }))}
            >
              Confirm return received
            </button>
          ) : null}
        </p>
      </section>
      <p>
        <Link href="/wardrobe" className="button button--secondary">
          Back to wardrobe
        </Link>
      </p>
    </>
  );
}

