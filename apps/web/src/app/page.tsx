"use client";

import { useRouter } from "next/navigation";
import { BriefFormView } from "../components/brief-form-view";

export default function Home() {
  const router = useRouter();
  return <BriefFormView onComplete={() => router.push("/studio")} />;
}
