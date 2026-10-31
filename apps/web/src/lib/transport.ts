/**
 * Transport selection for the browser UI.
 *
 * FIXTURE (default): the labelled in-browser transport, no server needed.
 * LIVE (NEXT_PUBLIC_TRANSPORT=live): the generated typed client against the
 * Anchor Fit API. Network operations are async on the live transport; UI call
 * sites await results, which is a no-op for the synchronous fixture.
 */
import { FixtureTransport, sharedTransport as sharedFixtureTransport } from "./fixture/transport";
import { LiveTransport } from "./live/transport";

export { freshTransport } from "./fixture/transport";
export type { FixtureError, FixtureResult } from "./fixture/transport";

export type UiTransport = FixtureTransport | LiveTransport;

export type TransportMode = "FIXTURE" | "LIVE";

export function transportMode(): TransportMode {
  return process.env.NEXT_PUBLIC_TRANSPORT === "live" ? "LIVE" : "FIXTURE";
}

/** Shared singleton for the browser UI, selected by NEXT_PUBLIC_TRANSPORT. */
export function sharedTransport(): UiTransport {
  if (transportMode() === "LIVE") {
    return liveTransport();
  }
  return sharedFixtureTransport();
}

let liveTransportInstance: LiveTransport | null = null;

function liveTransport(): LiveTransport {
  if (!liveTransportInstance) liveTransportInstance = new LiveTransport();
  return liveTransportInstance;
}
