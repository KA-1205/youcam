"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { sharedTransport } from "../../../lib/transport";
import { OrderView } from "../../../components/order-view";
import type { components } from "../../../../../../contracts/runtime/client";

type OrderSnapshot = components["schemas"]["OrderSnapshot"];

export default function OrderPage() {
  const params = useParams<{ orderId: string }>();
  const orderId = params?.orderId;
  const [order, setOrder] = useState<OrderSnapshot | null>(null);
  const [unknown, setUnknown] = useState(false);
  const [paymentUnknown, setPaymentUnknown] = useState(false);

  useEffect(() => {
    if (!orderId) return;
    void (async () => {
      const result = await sharedTransport().getOrder(orderId);
      if (result.data) {
        setOrder(result.data);
        setPaymentUnknown(sharedTransport().orderPaymentUnknown(orderId));
      } else {
        setUnknown(true);
      }
    })();
  }, [orderId]);

  if (unknown) {
    return (
      <>
        <h1>Order</h1>
        <p className="error-note" role="alert">
          This device has no such demo order. Orders live only in this fixture tab.
        </p>
        <p>
          <Link href="/wardrobe" className="button">
            Back to wardrobe
          </Link>
        </p>
      </>
    );
  }

  return (
    <>
      <h1>Order tracking</h1>
      {order ? <OrderView order={order} paymentUnknown={paymentUnknown} /> : <p className="loading-note">Loading…</p>}
    </>
  );
}
