"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/studio", label: "Studio" },
  { href: "/compare", label: "Compare" },
  { href: "/preview", label: "Preview" },
  { href: "/beauty", label: "Beauty" },
  { href: "/wardrobe", label: "Wardrobe" },
  { href: "/stylist", label: "Stylist" },
  { href: "/merchant", label: "Merchant" },
];

/** Fixture-mode banner copy. Never present sample data as live behavior. */
export const MODE_NOTICE =
  "FIXTURE MODE — this surface runs on labelled sample data. Live styling, previews and payment are not wired yet.";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "/";
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <Link href="/" className="brand">
            Anchor&nbsp;Fit
          </Link>
          <nav aria-label="Primary">
            <ul className="nav-list">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className={pathname === link.href ? "nav-link nav-link--active" : "nav-link"}
                    aria-current={pathname === link.href ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <p className="mode-banner" role="note">
          {MODE_NOTICE}
        </p>
      </header>
      <main id="main" className="site-main">
        {children}
      </main>
      <footer className="site-footer">
        <p>
          Anchor Fit — simulated store. Demo data only; no real payments, no live provider calls.
        </p>
      </footer>
    </>
  );
}
