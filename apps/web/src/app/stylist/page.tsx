"use client";

import { StylistConsoles } from "../../components/stylist-consoles";

export default function StylistPage() {
  return (
    <>
      <h1>Stylist</h1>
      <p className="lede">
        The stylist works only on sessions explicitly shared with them, proposes changes with
        recorded exceptions, and every application needs shopper approval.
      </p>
      <StylistConsoles />
    </>
  );
}
