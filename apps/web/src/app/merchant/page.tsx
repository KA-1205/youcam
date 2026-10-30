"use client";

import { MerchantConsoles } from "../../components/merchant-consoles";

export default function MerchantPage() {
  return (
    <>
      <h1>Merchant console</h1>
      <p className="lede">
        Capability readiness, catalog staging with explicit publication approval, and aggregate
        demo reporting for this storefront tenant.
      </p>
      <MerchantConsoles />
    </>
  );
}
