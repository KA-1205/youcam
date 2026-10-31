"use client";

import { ConsultationBook } from "../../components/consultation-book";

export default function ConsultationsPage() {
  return (
    <>
      <h1>Consultations</h1>
      <p className="lede">
        Book time with a store stylist. Any session shared for the appointment keeps the same scope
        and the seven-day access limit unless you renew it.
      </p>
      <ConsultationBook />
    </>
  );
}
