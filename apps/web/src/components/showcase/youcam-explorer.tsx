"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Arrow } from "./icons";

const FEATURES = [
  {
    title: "Clothes",
    subtitle: "See a different silhouette.",
    image: "editorial.jpg",
    alt: "Editorial portrait of a model in an oversized blazer",
    api: "YouCam Clothes V4",
    input: "A photo of you + permitted garment references",
    output: "A generated clothing preview",
    description:
      "Explore clothing changes with your own photo. Your styling board keeps track of the individual pieces; a preview helps you picture a direction.",
    status: "Live verification pending",
    details: ["Clothes V4"],
  },
  {
    title: "Makeup",
    subtitle: "Explore a new colour story.",
    image: "beauty.jpg",
    alt: "Editorial beauty portrait with red lipstick",
    api: "YouCam Makeup",
    input: "A face photo + selected makeup settings",
    output: "A makeup exploration preview",
    description:
      "Explore makeup effects alongside your look. Visual exploration is separate from an exact product or foundation-shade match.",
    status: "Live verification pending",
    details: ["Makeup"],
  },
  {
    title: "Jewellery",
    subtitle: "Find your finishing touch.",
    image: "jewellery.jpg",
    alt: "Editorial photograph of gold earrings on fabric",
    api: "YouCam jewellery & watch APIs",
    input: "A suitable photo + permitted accessory references",
    output: "A category-specific accessory preview",
    description:
      "Explore Earrings, Necklace, Ring, Bracelet and Watch previews individually. Each category has its own image requirements and readiness checks.",
    status: "Live verification pending",
    details: ["Earrings", "Necklace", "Ring", "Bracelet", "Watch"],
  },
  {
    title: "Hair colour",
    subtitle: "A different shade of you.",
    image: "editorial.jpg",
    alt: "Editorial portrait showing dark hair",
    api: "YouCam Hair Color",
    input: "A face photo + a supported colour preset",
    output: "A hair-colour exploration preview",
    description:
      "Try a supported hair-colour preset with a separately consented photo. Hair colour is for exploration and does not add a product to your basket.",
    status: "Live-tested integration",
    details: ["Hair Color"],
  },
] as const;

export function YoucamExplorer() {
  const [selected, setSelected] = useState(0);
  const feature = FEATURES[selected];
  return (
    <section
      id="youcam"
      className="showcase-section youcam-section"
      aria-labelledby="youcam-title"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">03 / POWERED BY YOUCAM</p>
          <h2 id="youcam-title">
            Picture the possibilities.
            <br />
            <span className="soft-text">Then make it yours.</span>
          </h2>
        </div>
        <p>
          From the outfit to the finishing touches.
          <br />
          Explore what each preview can do.
        </p>
      </div>
      <div className="youcam-explorer">
        <div
          className="capability-menu"
          role="group"
          aria-label="YouCam features"
        >
          {FEATURES.map((item, index) => (
            <button
              key={item.title}
              type="button"
              aria-pressed={selected === index}
              aria-controls="capability-detail"
              onClick={() => setSelected(index)}
            >
              <span className="capability-number">0{index + 1}</span>
              <span>
                <strong>{item.title}</strong>
                <small>{item.subtitle}</small>
              </span>
              <Arrow diagonal />
            </button>
          ))}
        </div>
        <div
          id="capability-detail"
          className="capability-detail"
          aria-live="polite"
          aria-atomic="true"
        >
          <div className={`capability-image capability-image--${selected}`}>
            <Image
              src={`/showcase/${feature.image}`}
              alt={feature.alt}
              fill
              sizes="(max-width: 760px) 100vw, 40vw"
            />
            <span className="image-caption">
              Editorial inspiration · not a YouCam result
            </span>
          </div>
          <div className="capability-copy">
            <span
              className={
                selected === 3 ? "readiness readiness--tested" : "readiness"
              }
            >
              {feature.status}
            </span>
            <h3>{feature.api}</h3>
            <p>{feature.description}</p>
            <div className="capability-tags">
              {feature.details.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
            <dl>
              <div>
                <dt>YOU PROVIDE</dt>
                <dd>{feature.input}</dd>
              </div>
              <div>
                <dt>YOU EXPLORE</dt>
                <dd>{feature.output}</dd>
              </div>
            </dl>
            <Link href="/preview" className="text-link">
              Open preview workspace <Arrow />
            </Link>
          </div>
        </div>
      </div>
      <p className="readiness-note">
        <strong>Hair Color · Live-tested integration.</strong> Previously tested
        end to end. Clothes, Makeup, Earrings, Necklace, Ring, Bracelet and
        Watch still need live verification. The preview workspace shows current
        availability; an active styling session and photo consent are required.
        Previews do not guarantee physical fit or an exact shade match.
      </p>
    </section>
  );
}
