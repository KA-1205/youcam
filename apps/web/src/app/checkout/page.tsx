"use client";

import { useRouter } from "next/navigation";
import { CheckoutView } from "../../components/checkout-view";

export default function CheckoutPage() {
  const router = useRouter();
  return <CheckoutView onOrderPlaced={(orderId) => router.push(`/orders/${orderId}`)} />;
}
