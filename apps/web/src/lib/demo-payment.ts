/** Demo server references are a closed set, unrelated to real payment instruments. */
export function demoPaymentReference(mode: "LIVE" | "FIXTURE", method: string): string {
  return mode === "LIVE" ? "demo-pay-success" : `demo-${method}`;
}
