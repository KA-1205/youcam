import Link from "next/link";
import { Arrow, Mark } from "./icons";

export function ShowcaseHeader() {
  return (
    <header className="showcase-header">
      <div className="showcase-header-inner">
        <Link href="/" className="showcase-brand" aria-label="Anchor Fit home">
          <Mark /> anchor fit<span className="brand-period">.</span>
        </Link>
        <nav aria-label="Primary">
          <a href="#how-it-works">How it works</a>
          <a href="#youcam">YouCam features</a>
          <Link href="/wardrobe">My wardrobe</Link>
        </nav>
        <Link href="/start" className="header-studio">
          Enter the studio <Arrow diagonal />
        </Link>
      </div>
    </header>
  );
}
