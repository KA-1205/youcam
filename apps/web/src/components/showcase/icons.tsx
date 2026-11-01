export function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h15m-6-6 6 6-6 6"}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Mark() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M16 3v26M3 16h26M7 7l18 18M7 25 25 7"
        stroke="currentColor"
        strokeWidth="3"
      />
      <circle cx="16" cy="16" r="5" fill="currentColor" />
    </svg>
  );
}

export function Lock() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="5"
        y="10"
        width="14"
        height="11"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}

/** Original vector sketches represent concepts, never catalog photographs. */
export function Garment({
  kind,
  tone = "#f2e9dc",
}: {
  kind: "top" | "trousers" | "shoes" | "earrings";
  tone?: string;
}) {
  return (
    <svg
      viewBox="0 0 200 220"
      fill="none"
      aria-hidden="true"
      className="garment-sketch"
    >
      {kind === "top" && (
        <>
          <path
            d="m63 30-38 23-19 56 38 12 11-30-5 104h100l-5-104 11 30 38-12-19-56-38-23c-6 20-68 20-74 0Z"
            fill={tone}
            stroke="#b9a89c"
            strokeWidth="1.5"
          />
          <path
            d="M63 30c8 32 66 32 74 0M57 180h86M50 73l5 18m90 0 5-18"
            stroke="#c8b8ac"
            strokeWidth="1.5"
          />
        </>
      )}
      {kind === "trousers" && (
        <>
          <path
            d="M49 20h102l17 183h-56l-12-115-12 115H32L49 20Z"
            fill={tone}
            stroke="#655a54"
            strokeWidth="1.5"
          />
          <path
            d="M48 36h105M100 36v52M72 36c-1 22-8 30-26 32m82-32c1 22 8 30 26 32M60 73l-9 119m89-119 9 119"
            stroke="#ffffff"
            strokeOpacity=".2"
            strokeWidth="1.5"
          />
          <circle cx="104" cy="28" r="2" fill="#c5ad83" />
        </>
      )}
      {kind === "shoes" && (
        <>
          <path
            d="M30 59c16-16 30-15 39 0l14 33 49 33c20 12 21 35 1 41-26 7-66 3-95-3-11-2-17-10-17-22L30 59Z"
            fill={tone}
            stroke="#655a54"
            strokeWidth="1.5"
          />
          <path
            d="M31 74c6 34 15 49 45 40M22 148c48 14 91 15 124 1M78 93l-14 9m24-3-14 9m24-2-14 9"
            stroke="#c4b8a8"
            strokeWidth="2"
          />
          <path
            d="M109 38c11-12 24-11 31 2l13 26 28 25c13 12 12 28 0 32l-24 2"
            stroke="#655a54"
            strokeWidth="1.5"
          />
        </>
      )}
      {kind === "earrings" && (
        <>
          <ellipse
            cx="61"
            cy="112"
            rx="28"
            ry="46"
            stroke="#9b7948"
            strokeWidth="9"
          />
          <ellipse
            cx="137"
            cy="112"
            rx="28"
            ry="46"
            stroke="#9b7948"
            strokeWidth="9"
          />
          <ellipse
            cx="61"
            cy="112"
            rx="28"
            ry="46"
            stroke="#dec99a"
            strokeWidth="3"
          />
          <ellipse
            cx="137"
            cy="112"
            rx="28"
            ry="46"
            stroke="#dec99a"
            strokeWidth="3"
          />
          <path d="M61 60v15m76-15v15" stroke="#9b7948" strokeWidth="5" />
        </>
      )}
    </svg>
  );
}
