# Anchor Fit — Reference Links

**30 October v3.3 update:** See `Anchor-Fit-YouCam-APIs.md` for the checked integration inventory. API documentation is not proof of account access. AI Look VTO applies facial/makeup templates, not combined apparel looks. Hair Color has a dedicated API at https://docs.perfectcorp.com/reference/ai_hair_color/v1.0. Perfect Beauty Agent remains an unverified candidate; Anchor Fit owns constraint validation.

Every link the PRD and spec rely on, grouped by what it is needed for. Links marked **PRD** came from your original PRD. Links marked **found** turned up in a search on 28 October 2026 and appeared in results; I did not open each page, so check before relying on details. A URL to open for context is not a guarantee of what it says today.

---

## 1. YouCam / Perfect Corp (try-on and analysis)

### Capabilities used in the PRD
| Need | Link | Source |
|---|---|---|
| Clothing try-on (V4), async tasks | https://docs.perfectcorp.com/reference/ai_clothes/v4.0 | PRD |
| Makeup try-on (foundation and other effects) | https://docs.perfectcorp.com/reference/makeup_vto/section/overview | PRD |
| Earrings try-on (shopper photo plus product reference) | https://docs.perfectcorp.com/reference/ai_earrings | PRD |
| Facial colour tones analyzer (optional) | https://docs.perfectcorp.com/reference/ai_skin_tone_analysis | PRD |

### Jewellery, hair and combined looks (needed for the jewellery add-on and extended try-on)
| Need | Link | Source |
|---|---|---|
| Release notes: lists necklace, ring, bracelet, watch, hairstyle, look, shoes, bag and more | https://docs.perfectcorp.com/release/changelog | found |
| Necklace try-on | https://docs.perfectcorp.com/reference/ai_necklace | found (path from release notes) |
| Ring try-on | https://docs.perfectcorp.com/reference/ring_vto | found (path from release notes) |
| Bracelet try-on | https://docs.perfectcorp.com/reference/ai_bracelet | found (path from release notes) |
| Watch try-on | https://docs.perfectcorp.com/reference/ai_watch | found (path from release notes) |
| Hairstyle try-on (not selected; use dedicated Hair Color API) | https://docs.perfectcorp.com/reference/ai_hairstyle | found (path from release notes) |
| Facial/makeup look templates (not a combined outfit endpoint) | https://docs.perfectcorp.com/reference/ai_look_vto | found (path from release notes) |
| Bracelet product page | https://yce.perfectcorp.com/ai-api/products/ai-bracelet-virtual-try-on-api | found |
| Jewellery API overview (blog) | https://www.perfectcorp.com/business/blog/retail/AI-Jewelry-api | found |
| Fashion API launch, 15 January 2026 | https://www.perfectcorp.com/business/news/new-api-fashion-category | found |

### Account, keys and tooling
| Need | Link | Source |
|---|---|---|
| API console: keys | https://yce.makeupar.com/api-console/en/api-keys/ | found |
| API playground for watch try-on | http://yce.makeupar.com/api-console/en/api-playground/ai-watch-virtual-try-on/ | found |
| Official YouCam skills (development helpers) | https://github.com/YouCam-API/skills | PRD |
| Official Beauty MCP | https://github.com/YouCam-API/beauty-skin-care-MCP | PRD |

**Open item**: the necklace, ring, bracelet, watch and hair-colour docs exist, but the PRD still gates each on a real-account call (region, version, pricing, image limits) before it is called integrated. The docs show the watch endpoint pattern as `POST /s2s/v2.0/task/2d-vto/watch` with polling by task ID, which fits the PRD's adapter and job-state design.

---

## 2. Hackathon

| Need | Link | Source |
|---|---|---|
| Overview | https://youcam-api-skin-ai-ecommerce.devpost.com/ | PRD |
| Rules | https://youcam-api-skin-ai-ecommerce.devpost.com/rules | PRD |

---

## 3. Competitive and design context (inspiration only; no code, branding, photos or catalogs may be reused without permission)

| Name | Link | Why it matters |
|---|---|---|
| Undertone | https://github.com/Chinmay-92/undertone | Beauty-and-jewellery chaining; API combination is not unique |
| Kasane | https://github.com/vn-envy/kasane | Owned-wardrobe recommendations |
| TryOnReady | https://github.com/jlhpacheco/tryonready-retail-platform | Boutique try-on operations; states what works and what is pending |
| Snap2Shelf | https://snap2shelf.vercel.app/ | Input-to-deliverable workflow; do not copy its pixel-preservation claim to generative try-on |
| Retrofit (YC) | https://www.ycombinator.com/companies/retrofit | Inspiration-driven catalog discovery |
| Short Story (YC) | https://www.ycombinator.com/companies/short-story | Focused style discovery and feedback |
| Clear (YC) | https://www.ycombinator.com/companies/clear | Product and outcome tracking; informs wardrobe and diary |
| Bezel (YC) | https://www.ycombinator.com/companies/bezel | Merchant creative workflows; informs lookbooks |

---

## 4. Payments (demo gateway and later real provider)

| Need | Link | Source |
|---|---|---|
| Razorpay test integration: test mode, mock bank page, `success@razorpay` and `failure@razorpay` UPI IDs | https://razorpay.com/docs/payments/payment-gateway/web-integration/custom/test-integration.md | found |
| Razorpay test card details and error-scenario cards (for decline, authentication and timeout simulations) | https://razorpay.com/docs/payments/payments/test-card-details | found (linked from the pages above) |
| Razorpay docs index | https://razorpay.com/docs/llms.txt | found |
| Stripe testing (alternative provider) | https://docs.stripe.com/testing | not searched; confirm before use |

Notes: Razorpay's test mode suppresses real notifications and skips 3D Secure and OTP flows in some cases, so the PRD's "authentication required" simulation needs the adapter's own fake rather than relying only on the provider's test mode. The local simulator and demo tax/shipping/return behaviour are selected in Behavior Contract §5. Live providers and real commercial/legal rules remain activation decisions.

---

## 5. Privacy and law (reference only; not legal advice)

| Need | Link | Source |
|---|---|---|
| India's DPDP Act, 2023 and framework (MeitY) | https://www.meity.gov.in/data-protection-framework | found |
| DPDP Rules, 2025 background (notified 13 November 2025) | https://www.dsci.in/content/data-protection-framework-india | found |
| Law-firm summary of the Act and Rules | https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force- | found |

The first-party retention requirements are defined in Behavior Contract §6; they are engineering acceptance requirements, not legal-compliance claims. A lawyer should review them against the Act and Rules, and against any other regimes if you serve users elsewhere. The framework page also mentions a pending Supreme Court challenge to some provisions, so check current status.

---

## 6. Accessibility

| Need | Link | Source |
|---|---|---|
| WCAG 2.2 (the PRD's target level is AA) | https://www.w3.org/TR/WCAG22/ | standard W3C address; not searched |

---

## 7. Process and tooling

| Need | Link | Source |
|---|---|---|
| GitHub Spec Kit (spec.md, plan.md, tasks.md workflow) | https://github.com/github/spec-kit | named in the spec-kit skill |

---

## 8. Files in this project

| File | Purpose |
|---|---|
| `Anchor-Fit-PRD.md` | Full-project PRD in Spec Kit style (v3.3) |
| `anchor-fit-spec.md` | Product spec with user stories, decisions, testing and scope |
| Visual reference canvas | https://claude.ai/artifact/8awk1WkzMgqqfxun8xCymD (studio, compare, stylist, jewellery screens; wardrobe and checkout screens not yet drawn) |

## Final contract additions

- Anchor-Fit-Behavior-Contract.md: resolved v3.3 behaviour defaults and empirical gates.
- Anchor-Fit-AI-Stylist-Spec.md and accompanying JSON schemas: internal interfaces.
- Anchor-Fit-Delivery-Checklist.md: screen behaviour, demonstration script and external evidence.
- Model adapter documentation: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash (text/image input and structured output documented; account untested).
- Authoritative rules: https://youcam-api-skin-ai-ecommerce.devpost.com/rules (checked 30 October 2026). Third-party materials in the video require permission; the rules do not ban every authorized trademark. Use the current official rules for final submission decisions.

Older research leads above are context, not competing product requirements. Payment test-provider links do not select a live provider; the current payment adapter is a local simulation. Physical privacy/legal compliance is not established by this reference list.
