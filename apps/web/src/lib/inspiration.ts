/** Shopper extensions: inspiration search, guided entry, consultation slots
 * and partner-widget launch-context checks. Pure and fixture-backed. */
import { VARIANTS } from "./fixture/demo-catalog";


export type InspirationResult = {
  variantId: string;
  title: string;
  brand: string;
  slot: string;
  priceMinor: number | null;
  attributesUnknown: boolean;
};

export function searchCatalog(query: string): InspirationResult[] {
  const q = query.trim().toLowerCase();
  if (q === "") return [];
  return VARIANTS.filter(
    (v) =>
      v.brandName.toLowerCase().includes(q) ||
      v.slot.replaceAll("_", " ").toLowerCase().includes(q) ||
      v.variantId.toLowerCase().includes(q),
  ).map((v) => ({
    variantId: v.variantId,
    title: v.brandName,
    brand: v.brandName,
    slot: v.slot,
    priceMinor: v.priceMinor,
    attributesUnknown: Object.keys(v.attributes).length === 0,
  }));
}

export type Suggestion = { prompt: string; target: { href: string; label: string } };

/** Guided entry chips. Each routes to the same validated actions, never a side door. */
export const SUGGESTIONS: Suggestion[] = [
  { prompt: "Build a complete outfit around a top I own", target: { href: "/", label: "Build a complete outfit" } },
  { prompt: "Compare up to three alternatives", target: { href: "/compare", label: "Compare looks" } },
  { prompt: "Preview clothing on a photo", target: { href: "/preview?capability=CLOTHES_V4", label: "Clothing preview" } },
  { prompt: "Explore makeup and jewellery", target: { href: "/beauty", label: "Beauty and jewellery" } },
  { prompt: "Show me what I own", target: { href: "/wardrobe", label: "Open wardrobe" } },
];

export function conversationTarget(key: string): { href: string; label: string } | null {
  return SUGGESTIONS.find((s) => s.prompt.toLowerCase().includes(key.toLowerCase()))?.target ?? null;
}

export type ConsultationSlot = {
  slotId: string;
  startMinutes: number;
  durationMinutes: 30;
  label: string;
  booked: boolean;
};

export type Booking = { slotId: string; date: string };

/** Internal 30-minute slots in tenant timezone; fixture keeps them local. */
export function consultationSlots(date: string, timezone: string, bookings: Booking[] = []): ConsultationSlot[] {
  const taken = new Set(bookings.filter((b) => b.date === date).map((b) => b.slotId));
  return Array.from({ length: 10 }, (_, i) => {
    const startMinutes = 10 * 60 + i * 30;
    const slotId = `${date}-slot-${i}`;
    const hour = Math.floor(startMinutes / 60);
    const minute = startMinutes % 60;
    return {
      slotId,
      startMinutes,
      durationMinutes: 30 as const,
      label: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")} (${timezone})`,
      booked: taken.has(slotId),
    };
  });
}

export type WidgetContext =
  | { authorized: true; variantId: string }
  | { authorized: false; reason: string };

/**
 * Partner widgets forward an exact variant id via signed launch context.
 * Without it the widget refuses to render product data.
 */
export function widgetContext(params: URLSearchParams): WidgetContext {
  const launch = params.get("launch");
  const variantId = params.get("variant");
  if (!launch) {
    return { authorized: false, reason: "Missing launch context. Open this widget from the partner site." };
  }
  if (!variantId || !VARIANTS.some((v) => v.variantId === variantId)) {
    return { authorized: false, reason: "Unknown product in launch context." };
  }
  return { authorized: true, variantId };
}
