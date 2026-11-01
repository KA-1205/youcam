import Image from "next/image";
import Link from "next/link";
import { Arrow, Garment, Lock, Mark } from "./icons";

export function ShowcaseHero() {
  return (
    <section className="showcase-hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <p className="eyebrow">
          <span className="eyebrow-line" /> YOUR STYLE. A NEW STARTING POINT.
        </p>
        <h1 id="hero-title">
          One piece you love.
          <br />
          <span>
            A look that’s
            <br />
            all you.
          </span>
        </h1>
        <p className="hero-description">
          Your favourite top. That one great find.
          <br />
          Build a look around it, explore the finishing touches,
          <br className="desktop-break" /> and picture the possibilities with
          YouCam.
        </p>
        <div className="hero-actions">
          <Link href="/start" className="showcase-button">
            Build my look <Arrow />
          </Link>
          <a href="#example" className="text-link">
            Explore an example <Arrow diagonal />
          </a>
        </div>
        <p className="hero-note">
          <Lock /> Your anchor stays. The possibilities change.
        </p>
      </div>
      <div className="hero-visual">
        <div className="hero-photo">
          <Image
            src="/showcase/editorial.jpg"
            alt="Editorial fashion inspiration: a model wearing an oversized blazer"
            fill
            priority
            sizes="(max-width: 760px) 90vw, 45vw"
          />
          <span className="photo-overline">THE ART OF PUTTING IT TOGETHER</span>
          <span className="photo-index">ANCHOR FIT / THE FIRST EDIT</span>
        </div>
        <div className="hero-anchor">
          <span className="eyebrow">IT STARTS WITH ONE PIECE</span>
          <Garment kind="top" />
          <div>
            <span className="anchor-status">
              <Lock /> THE ANCHOR
            </span>
            <strong>Your favourite top</strong>
            <small>A little inspiration to start.</small>
          </div>
        </div>
        <span className="hero-seal">
          <Mark />
          <span>
            ALREADY YOU.
            <br />
            NEW POSSIBILITIES.
          </span>
        </span>
        <p className="editorial-label">
          Editorial photography · styling inspiration, not a YouCam result
        </p>
      </div>
    </section>
  );
}
