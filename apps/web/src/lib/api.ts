import createClient from "openapi-fetch";
import type { paths } from "../../../../contracts/runtime/client";
export const api = createClient<paths>({ baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000", credentials: "include" });
