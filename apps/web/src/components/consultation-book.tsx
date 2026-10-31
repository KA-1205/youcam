"use client";

import { useState } from "react";
import { consultationSlots, type Booking } from "../lib/inspiration";

const DATES = ["2026-11-02", "2026-11-03", "2026-11-04"] as const;
const TIMEZONE = "Asia/Kolkata";

export function ConsultationBook() {
  const [date, setDate] = useState<string>(DATES[0]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const slots = consultationSlots(date, TIMEZONE, bookings);

  function onBook(slotId: string) {
    setBookings((prev) => [...prev, { slotId, date }]);
    setMessage(
      "Consultation held locally in this fixture. A real deployment reserves the slot for a named stylist and expires shared access after seven days unless renewed.",
    );
  }

  function onCancel(slotId: string) {
    setBookings((prev) => prev.filter((b) => !(b.slotId === slotId && b.date === date)));
    setMessage("Consultation cancelled. The slot is open again.");
  }

  return (
    <section className="card" aria-label="Consultations">
      <h2>Book a consultation</h2>
      <p className="footnote">
        Internal 30-minute slots in the tenant timezone ({TIMEZONE}). Booking is explicit and can be
        cancelled — no video provider is involved.
      </p>
      <div className="tab-row" role="tablist" aria-label="Consultation date">
        {DATES.map((d) => (
          <button
            key={d}
            type="button"
            role="tab"
            aria-selected={date === d}
            className={date === d ? "tab tab--active" : "tab"}
            onClick={() => setDate(d)}
          >
            {d}
          </button>
        ))}
      </div>
      <ul className="item-list">
        {slots.map((slot) => (
          <li key={slot.slotId}>
            <div className="item-row">
              <span>
                {slot.label} · {slot.durationMinutes} min
              </span>
              {slot.booked ? (
                <button type="button" className="button button--secondary" onClick={() => onCancel(slot.slotId)}>
                  Cancel consultation
                </button>
              ) : (
                <button type="button" className="button" onClick={() => onBook(slot.slotId)}>
                  Book
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {message ? (
        <p role="status" className="mode-note">
          {message}
        </p>
      ) : null}
    </section>
  );
}
