"use client";

import { useRouter } from "next/navigation";
import { BriefFormView } from "../../components/brief-form-view";

export default function StartPage() {
  const router = useRouter();
  return <BriefFormView onComplete={() => router.push("/studio")} />;
}
