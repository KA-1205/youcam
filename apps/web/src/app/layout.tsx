import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "../components/app-shell";
import { SessionProvider } from "../lib/session-context";
import { ShortlistProvider } from "../lib/shortlist-context";

export const metadata: Metadata = {
  title: "Anchor Fit",
  description: "Build, preview, and shop a look around one item.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <ShortlistProvider>
            <AppShell>{children}</AppShell>
          </ShortlistProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
