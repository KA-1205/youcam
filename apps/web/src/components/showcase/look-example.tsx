"use client";

import Link from "next/link";
import { useState } from "react";
import { Arrow, Garment, Lock } from "./icons";

const OCCASIONS = {
  Everyday: {
    name: "The everyday edit",
    bottom: "Relaxed trousers",
    tone: "#9b9d93",
    shoes: "Easy flats",
    shoeTone: "#b09b82",
    reason:
      "An easy silhouette and muted tones, built around the top you already love.",
  },
  Workday: {
    name: "A little more polished",
    bottom: "Tailored trousers",
    tone: "#75645d",
    shoes: "Classic loafers",
    shoeTone: "#46332b",
    reason:
      "Structured separates take your favourite top from casual to considered.",
  },
  Evening: {
    name: "Out after hours",
    bottom: "Dark wide-leg trousers",
    tone: "#463845",
    shoes: "Evening flats",
    shoeTone: "#392e31",
    reason:
      "Deeper tones and a small metallic accent give the same anchor a different mood.",
  },
} as const;

export function LookExample() {
  const [occasion, setOccasion] = useState<keyof typeof OCCASIONS>("Everyday");
  const [budget, setBudget] = useState("1500");
  const look = OCCASIONS[occasion];
  const withJewellery = budget === "2500";

  return (
    <section
      id="example"
      className="showcase-section example-section"
      aria-labelledby="example-title"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">01 / THE ANCHOR EFFECT</p>
          <h2 id="example-title">
            Same favourite.
            <br />
            <span className="soft-text">A fresh perspective.</span>
          </h2>
        </div>
        <p>
          Keep the piece that feels like you.
          <br />
          Explore what goes with it.
        </p>
      </div>
      <div className="look-example">
        <div className="look-board">
          <div className="board-caption">
            <span className="eyebrow">YOUR LOOK, REIMAGINED</span>
            <span className="mini-label">Illustrative styling example</span>
          </div>
          <div className="board-items">
            <figure className="board-anchor">
              <div className="sketch-stage">
                <Garment kind="top" />
              </div>
              <figcaption>
                <span>
                  <Lock /> YOUR ANCHOR
                </span>
                <strong>Your favourite top</strong>
                <small>Already yours · ₹0 new spend</small>
              </figcaption>
            </figure>
            <span className="board-plus" aria-hidden="true">
              +
            </span>
            <figure className="board-bottom">
              <div className="sketch-stage">
                <Garment kind="trousers" tone={look.tone} />
              </div>
              <figcaption>
                <strong>{look.bottom}</strong>
                <small>₹650 · example price</small>
              </figcaption>
            </figure>
            <figure className="board-shoes">
              <div className="sketch-stage">
                <Garment kind="shoes" tone={look.shoeTone} />
              </div>
              <figcaption>
                <strong>{look.shoes}</strong>
                <small>₹750 · example price</small>
              </figcaption>
            </figure>
            {withJewellery && (
              <figure className="board-jewellery">
                <div className="sketch-stage">
                  <Garment kind="earrings" />
                </div>
                <figcaption>
                  <strong>Finishing hoops</strong>
                  <small>₹700 · example price</small>
                </figcaption>
              </figure>
            )}
          </div>
          <p className="board-note">
            Original sketches and example prices. This board is not a live
            recommendation or a shoppable catalog.
          </p>
        </div>
        <div className="example-controls">
          <p className="eyebrow">A SMALL CHANGE. A DIFFERENT LOOK.</p>
          <h3>
            Make room for
            <br />
            your kind of day.
          </h3>
          <fieldset className="occasion-picker">
            <legend>Pick an occasion</legend>
            <div>
              {Object.keys(OCCASIONS).map((name) => (
                <button
                  type="button"
                  key={name}
                  aria-pressed={occasion === name}
                  onClick={() => setOccasion(name as keyof typeof OCCASIONS)}
                >
                  {name}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="example-budget" htmlFor="example-budget">
            New-spend budget
            <select
              id="example-budget"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
            >
              <option value="1500">Up to ₹1,500</option>
              <option value="2500">Up to ₹2,500</option>
            </select>
          </label>
          <div className="example-result" aria-live="polite" aria-atomic="true">
            <h4>{look.name}</h4>
            <p>{look.reason}</p>
            <div className="example-total">
              <span>Example new spend</span>
              <strong>{withJewellery ? "₹2,100" : "₹1,400"}</strong>
            </div>
            <p className="example-budget-note">
              {withJewellery
                ? "Room for a finishing touch. Hoops added."
                : "A complete base look. Jewellery left out to keep spending down."}
            </p>
          </div>
          <Link href="/start" className="text-link">
            Create your own brief <Arrow />
          </Link>
        </div>
      </div>
    </section>
  );
}
