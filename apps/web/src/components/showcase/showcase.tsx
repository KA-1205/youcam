import Link from "next/link";
import { Arrow, Garment, Mark } from "./icons";
import { ShowcaseHero } from "./showcase-hero";
import { LookExample } from "./look-example";
import { YoucamExplorer } from "./youcam-explorer";

const STEPS = [
  [
    "Choose your anchor",
    "A favourite you own, or a piece from the catalog. Start with something you want to keep.",
  ],
  [
    "Set the brief",
    "Your occasion, categories and budget give the look a direction. You decide the boundaries.",
  ],
  [
    "Explore the looks",
    "Compare suggestions, lock the pieces you love and explore alternatives for the rest.",
  ],
  [
    "Picture it on you",
    "Open a supported YouCam preview, choose the settings and consent before uploading a photo.",
  ],
  [
    "Keep what works",
    "Save pieces, revisit your wardrobe or use the demo checkout for eligible catalog items.",
  ],
];

const QUESTIONS = [
  [
    "What makes an item an anchor?",
    "It is the piece your look is built around. It can be an item you already own or a catalog selection. The styling flow keeps it in the look while exploring complementary pieces.",
  ],
  [
    "Do I have to upload a photo?",
    "No. You can explore the styling workflow without one. Photo processing is a separate, explicit choice in the preview workspace. Current photo features are for adults who have permission to use the images.",
  ],
  [
    "Are all the YouCam previews available?",
    "Availability is shown per category in the preview workspace. Hair Color has prior end-to-end live test evidence. The other seven render adapters still require live verification. Separate previews are not presented as one verified combined makeover.",
  ],
  [
    "Can I buy the pieces here?",
    "The current application uses a synthetic catalog and simulated checkout. No real payment is taken. Hair colour remains exploration-only, and makeup shopping needs a verified exact product mapping.",
  ],
  [
    "What happens if the AI stylist is unavailable?",
    "The application can return labelled rule-based suggestions. You can still browse and compare the available pieces. It does not present fallback suggestions as output from an AI model.",
  ],
];

export function Showcase() {
  return (
    <div className="showcase">
      <ShowcaseHero />
      <div className="showcase-principles" aria-label="The Anchor Fit approach">
        <p>
          <span>01</span> Start with what you love
        </p>
        <span className="principle-star" aria-hidden="true">
          ✳
        </span>
        <p>
          <span>02</span> Work with your budget
        </p>
        <span className="principle-star" aria-hidden="true">
          ✳
        </span>
        <p>
          <span>03</span> Explore with YouCam
        </p>
      </div>
      <LookExample />
      <section
        id="how-it-works"
        className="showcase-section workflow-section"
        aria-labelledby="workflow-title"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">02 / FROM ONE PIECE TO YOUR NEXT LOOK</p>
            <h2 id="workflow-title">
              A little direction.
              <br />A lot more you.
            </h2>
          </div>
          <Link href="/start" className="text-link">
            Step into the studio <Arrow />
          </Link>
        </div>
        <ol className="showcase-steps">
          {STEPS.map(([title, description], index) => (
            <li key={title}>
              <span className="step-number">0{index + 1}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </li>
          ))}
        </ol>
      </section>
      <YoucamExplorer />
      <section
        className="showcase-section wardrobe-section"
        aria-labelledby="wardrobe-title"
      >
        <div className="wardrobe-art">
          <span className="eyebrow">MORE WEAR. MORE WAYS.</span>
          <div className="wardrobe-sketches">
            <div>
              <Garment kind="top" />
              <span>Already yours</span>
            </div>
            <div>
              <Garment kind="trousers" tone="#82706a" />
              <span>Something new</span>
            </div>
            <div>
              <Garment kind="earrings" />
              <span>A finishing touch</span>
            </div>
          </div>
          <p>Your wardrobe is a starting point.</p>
        </div>
        <div className="wardrobe-copy">
          <p className="eyebrow">04 / THE GOOD PIECES STAY</p>
          <h2 id="wardrobe-title">
            Build on what
            <br />
            you already love.
          </h2>
          <p>
            A fresh look doesn’t have to mean starting over. Keep owned pieces
            in the picture, compare your options and save the ones worth coming
            back to.
          </p>
          <div className="wardrobe-links">
            <Link href="/wardrobe" className="text-link">
              Explore your wardrobe <Arrow />
            </Link>
            <Link href="/compare" className="text-link">
              Compare your looks <Arrow />
            </Link>
          </div>
        </div>
      </section>
      <section
        id="questions"
        className="showcase-section questions-section"
        aria-labelledby="questions-title"
      >
        <div>
          <p className="eyebrow">A FEW THINGS TO KNOW</p>
          <h2 id="questions-title">
            Before you
            <br />
            make it yours.
          </h2>
        </div>
        <div className="showcase-faq">
          {QUESTIONS.map(([question, answer]) => (
            <details key={question}>
              <summary>
                {question}
                <span aria-hidden="true">+</span>
              </summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>
      <section className="showcase-cta">
        <Mark />
        <p className="eyebrow">START WITH SOMETHING YOU LOVE</p>
        <h2>
          The rest can
          <br />
          come together.
        </h2>
        <Link href="/start" className="showcase-button">
          Build my look <Arrow />
        </Link>
        <p className="cta-note">Explore the sample catalog. No real payment.</p>
      </section>
      <footer className="showcase-footer">
        <div>
          <Link href="/" className="showcase-brand">
            <Mark /> anchor fit<span className="brand-period">.</span>
          </Link>
          <p>Built around you. Powered by possibility.</p>
        </div>
        <nav aria-label="Showcase footer">
          <Link href="/start">Build a look</Link>
          <Link href="/preview">YouCam previews</Link>
          <Link href="/beauty">Beauty & jewellery</Link>
          <Link href="/wardrobe">Wardrobe</Link>
          <Link href="/merchant">For partners</Link>
          <a href="#questions">Questions</a>
        </nav>
        <div className="footer-bottom">
          <span>Anchor Fit · YouCam-powered virtual previews</span>
          <span>Sample catalog · Simulated checkout · Photos by consent</span>
          <a href="/showcase/credits.txt">
            Image & font credits <Arrow diagonal />
          </a>
        </div>
      </footer>
    </div>
  );
}
