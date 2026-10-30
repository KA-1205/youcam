const FLOW = [
  {
    href: "/studio",
    title: "Build the look",
    body: "Start from one item you own or one from the catalog, set your brief, and compare up to three alternatives.",
  },
  {
    href: "/preview",
    title: "See it on you",
    body: "Upload a photo with explicit consent for each use. Categories run separately and results stay labelled.",
  },
  {
    href: "/beauty",
    title: "Beauty and jewellery",
    body: "Makeup, hair colour and jewellery explorations with evidence labels, not guarantees.",
  },
  {
    href: "/wardrobe",
    title: "Wardrobe",
    body: "Everything you own, ordered or saved in one place, with provenance you can check.",
  },
  {
    href: "/stylist",
    title: "Stylist console",
    body: "A store stylist works only on sessions explicitly shared with them, and every change needs approval.",
  },
  {
    href: "/merchant",
    title: "Merchant console",
    body: "Catalog staging, capability readiness and aggregate reporting for the storefront operator.",
  },
];

export default function Home() {
  return (
    <>
      <h1>Start with one item.</h1>
      <p className="lede">
        Anchor Fit builds a coordinated look around something you already own or pick from the
        authorized catalog — then previews it, checks the budget, and keeps the choices explainable.
      </p>
      <p className="mode-note" role="status">
        FIXTURE MODE — every screen here runs on labelled sample data. Live styling, photo previews
        and payment are not available yet.
      </p>
      <ul className="flow-grid">
        {FLOW.map((card) => (
          <li key={card.href} className="flow-card">
            <a href={card.href}>
              <h2>{card.title}</h2>
              <p>{card.body}</p>
            </a>
          </li>
        ))}
      </ul>
      <p className="footnote">
        The compare and shortlist surfaces live inside the studio flow:{" "}
        <a href="/compare">open compare</a>.
      </p>
    </>
  );
}
