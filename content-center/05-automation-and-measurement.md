# Anansi Atlas — Content Automation & Measurement System

> The operating system for the Anansi Atlas content center. Built for a non-technical founder (Marcus Scott) to actually run.
> Goal it serves: recruit **19–20 nonprofit / mission-driven organizations** into the **Founding Atlas Partners Pilot** ($150/mo locked for life, first 20 orgs).
> Signup / apply link (use everywhere): **https://anansiatlas.com/anansi-atlas/**
> Platform priority: **LinkedIn first**, then Instagram, then TikTok. Product-forward, not founder-story-forward.

---

## PART 1 — Automated Content Creation Workflow

This is one assembly line. An idea goes in one end; a scheduled post, a captured lead, and a performance number come out the other. Every stage says **what tool runs it**, **what goes in**, **what comes out**, and **the exact hand-off** to the next stage.

Two stacks are given. **Start on the Minimum Viable Stack.** Only move to the Scaled Stack once you're posting 5+ times a week and it feels like manual work is the bottleneck.

### The two stacks at a glance

| Layer | Minimum Viable Stack (start here) | Scaled Stack (later) |
|---|---|---|
| Idea capture | Google Form → Google Sheet | Notion / Airtable form |
| Content database | **Google Sheet** (the Master Table from Part 2) | Airtable base |
| Writing (caption/script) | Claude (chat) with saved prompts | Claude via n8n, auto-drafted into the DB |
| Graphics | Canva (free) + manual prompt | Canva Bulk Create + AI image prompt |
| Approval | A "Status" column you flip to Approved | Notion board / Airtable Kanban |
| Scheduling | **Buffer free** (LinkedIn + IG) | Later or Buffer paid (adds TikTok, more channels) |
| Engagement tracking | Native analytics + a weekly Sheet | n8n pulls metrics into the DB nightly |
| Lead capture | LinkedIn DMs + the signup link | Zapier: form fill → CRM row → Slack ping |
| Follow-up | Saved DM templates | Automated reminder tasks |
| Cost | **$0–$6/mo** | ~$40–$80/mo |

Do NOT buy the scaled stack on day one. The whole Part-1 workflow runs on the free tiers.

---

### Stage-by-stage

#### Stage 1 — Idea Capture
- **Tool:** Google Form (one field: "Raw idea"; optional: pillar, platform). Answers land in a Google Sheet tab called `Inbox`.
- **Input:** A half-formed thought — "show the Opportunity Web orbiting a nonprofit's mission," "explain what a readiness gap is."
- **Output:** One row in `Inbox` with the raw idea and a timestamp.
- **Hand-off:** Once a week you triage `Inbox`: delete duds, and copy keepers into the **Master Table** (Part 2), assigning them a Date, Platform, and Content pillar.

**Content pillars** (keep every idea inside these five — they map to the brand):
1. **The Platform / Product** — real UI: Opportunity Web, Snapshot, Dashboard.
2. **The Problem** — scattered opportunity, buried in portals/spreadsheets/inboxes.
3. **Educational** — what a readiness gap is, funder vs. partner pathways, government pathways.
4. **Proof / Pilot** — the Founding Partners cohort, what a Snapshot reveals, the offer.
5. **Category Vocabulary** — Funders · Partners · Government · Resources · Readiness · Pathways.

#### Stage 2 — Content Calendar
- **Tool:** The Master Table (Google Sheet) sorted by `Date`. A calendar view is optional; the sorted sheet *is* the calendar.
- **Input:** Triaged ideas with a Platform and pillar.
- **Output:** A dated queue — you can see "Monday = LinkedIn product post, Wednesday = educational carousel."
- **Rhythm target (pre-launch):** LinkedIn 4×/week, Instagram 3×/week, TikTok 2×/week. Rotate pillars so you're never two product posts in a row.
- **Hand-off:** Each row with a Date and empty `Draft caption` is a work order for Stage 3.

#### Stage 3 — Post / Caption Generation
- **Tool:** Claude (chat). Paste the **brand brief** + one saved prompt.
- **Input:** The row's Hook + Content pillar + Platform.
- **Output:** A finished caption in the brand voice (clear, practical, strategic, warm, credible — never hype, never charity-toned), pasted into `Draft caption`.
- **Saved prompt (copy-paste):**
  > "You write for Anansi Atlas, a nonprofit opportunity intelligence platform (tagline: The Web of Opportunity). Voice: clear, practical, strategic, warm, credible, conversion-focused. NOT hype, NOT corporate, NOT charity-toned. We recruit nonprofits into the Founding Atlas Partners Pilot ($150/mo locked for life, first 20 orgs). Product node vocabulary: Funders, Partners, Government, Resources, Readiness, Pathways. CTA link: https://anansiatlas.com/anansi-atlas/. Write a [PLATFORM] post for this pillar [PILLAR] and hook [HOOK]. Keep it under [X] words. End with a soft CTA. Do not promise guaranteed funding, do not advertise a free Snapshot."
- **Hand-off:** Caption filled → move to Stage 4 (graphic) and Stage 5 (script, if video).

#### Stage 4 — Graphic Prompt Generation
- **Tool:** Claude writes the design brief → **Canva** builds it (or Canva's AI image tool consumes the prompt).
- **Input:** `Visual idea` column + brand visual direction.
- **Output:** A ready-to-build graphic brief AND the finished Canva asset.
- **Brand visuals (bake into every prompt):** dark navy + charcoal + **gold accents**; clean product-UI / dashboard shots; subtle web / network / pathway motif; Fraunces serif headings + Inter/DM Sans body; teal = strength, gold = gap. **Avoid:** cartoon spiders, mystical folklore imagery, generic stock SaaS art.
- **Hand-off:** Canva asset saved and linked in the sheet (paste the Canva share link into a notes cell).

#### Stage 5 — Video Script Generation (Reels / TikTok)
- **Tool:** Claude with a script prompt → filmed on phone or built in Canva.
- **Input:** The Hook + pillar, for `Post type = Reel/Short`.
- **Output:** A 20–40 sec script: **Hook (0–3s) → 1 problem line → 2–3 payoff lines showing the platform → CTA**.
- **Hand-off:** Script pasted into notes; film or animate; export vertical 9:16 into Canva; link the file.

#### Stage 6 — Approval
- **Tool:** A `Status` column: `Draft → Needs review → Approved → Scheduled → Posted`.
- **Input:** A row with caption + asset done.
- **Output:** Marcus reads it once, flips to `Approved`. This is the single quality gate — nothing schedules without it.
- **Hand-off:** `Approved` rows are eligible for Stage 7.

#### Stage 7 — Scheduling
- **Tool:** **Buffer (free)** for LinkedIn + Instagram. Add Later or Buffer paid when you turn on TikTok.
- **Input:** Approved caption + asset + Date.
- **Output:** Post queued in Buffer at the chosen time. Flip `Status` to `Scheduled`.
- **Hand-off:** Buffer auto-publishes. Change `Status` to `Posted`.

#### Stage 8 — Tracking Engagement
- **Tool (MVP):** Native analytics (LinkedIn post analytics, Instagram Insights) → typed weekly into the **Measurement sheet** (Part 3). **Tool (scaled):** n8n pulls metrics nightly into the DB.
- **Input:** Posted content.
- **Output:** Impressions, profile views, link clicks, comments, DMs started per post.
- **Hand-off:** Numbers feed Part 3's dashboard and the weekly review.

#### Stage 9 — Capturing Leads
- **Tool:** The signup link (https://anansiatlas.com/anansi-atlas/) in every CTA + LinkedIn DMs. **Scaled:** Zapier writes each application into a simple CRM sheet and pings Slack.
- **Input:** A commenter, a profile viewer, someone who clicked the link.
- **Output:** A named lead in a `Leads` tab: name, org, source post, stage (`New → Talking → Applied → Booked → Joined`).
- **Hand-off:** Any lead not yet `Applied` goes to Stage 10.

#### Stage 10 — Follow-up Messages
- **Tool:** LinkedIn DMs with saved templates (Claude drafts, you personalize the first line).
- **Input:** A `Leads` row in `New` or `Talking`.
- **Output:** A sent, personalized DM. Update the lead's stage.
- **Template (first touch, product-forward):**
  > "Hi [Name] — saw you [engaged with the post on readiness gaps]. Anansi Atlas maps the whole web of opportunity around a nonprofit's mission — funders, partners, government pathways — into one Opportunity Web Snapshot. We're taking 20 founding orgs at $150/mo locked for life. Want me to send you what the Snapshot actually shows? [link]"

#### Stage 11 — Content Performance Review
- **Tool:** The Part-3 dashboard + a 30-minute Friday ritual.
- **Input:** A full week of per-post metrics + lead stages.
- **Output:** 3 decisions: (1) which hook/pillar to make more of, (2) which to retire, (3) which post to **repurpose** (the `Repurpose option` column). Loop the winners back into Stage 1.

---

### Concrete example — one idea through the whole pipeline

1. **Idea (S1):** Google Form entry — "Show the Opportunity Web orbiting YOUR MISSION."
2. **Calendar (S2):** Becomes a Master Table row: Date = next Tuesday, Platform = LinkedIn, Pillar = Platform/Product, Post type = Carousel.
3. **Caption (S3):** Claude returns: *"Your nonprofit is surrounded by opportunity. It's just scattered — across funder portals, inboxes, spreadsheets, and someone's memory. The Opportunity Web puts your mission at the center and maps what's actually around it: Funders. Partners. Government. Resources. Readiness. Pathways. One picture instead of forty tabs. →"*
4. **Graphic (S4):** Canva builds a navy carousel — slide 1 the orb-web hero with pill nodes orbiting a gold "YOUR MISSION" hub; slides 2–5 zoom each node; gold accents throughout.
5. **Script (S5):** Skipped (carousel, not video).
6. **Approval (S6):** Marcus reads, flips to `Approved`.
7. **Schedule (S7):** Queued in Buffer for Tuesday 8:30am. `Status = Scheduled`.
8. **Track (S8):** By Friday: 1,900 impressions, 60 profile views, 22 link clicks, 9 comments.
9. **Capture (S9):** 3 commenters are nonprofit EDs → added to `Leads` as `New`.
10. **Follow-up (S10):** DM template sent to all 3; 1 replies → moved to `Talking`.
11. **Review (S11):** Best link-click rate of the week → mark for `Repurpose` as a TikTok voiceover; make two more product-node posts.

---

## PART 2 — Automation-Ready Master Table (content database schema)

This is the one table every idea lives in. In Google Sheets (or Airtable) make each of these a column. Every row is one post. `Status` (add as a 13th column) drives the assembly line: `Draft → Needs review → Approved → Scheduled → Posted`.

**Columns:** Date · Platform · Account · Content pillar · Post type · Hook · Draft caption · Visual idea · CTA · Link to use · Follow-up action · Repurpose option

> Link to use is the same everywhere: `https://anansiatlas.com/anansi-atlas/`. Account is Marcus Scott's LinkedIn or the Anansi Atlas brand handle.

| Date | Platform | Account | Content pillar | Post type | Hook | Draft caption | Visual idea | CTA | Link to use | Follow-up action | Repurpose option |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Mon | LinkedIn | Marcus Scott | Problem | Text post | "Your next funder is already out there. You just can't see them yet." | Nonprofits aren't short on opportunity — they're short on *visibility* into it. Funders, partners, and government pathways are scattered across portals, inboxes, and someone's memory. Anansi Atlas maps that whole web around your mission, so scattered opportunity becomes focused action. | Navy card, gold headline, faint web lines behind the text | "See what's around your mission →" | anansiatlas.com/anansi-atlas/ | Reply to every comment within 2h; DM nonprofit EDs | Turn into a 30s Reel voiceover |
| Tue | LinkedIn | Anansi Atlas | Platform/Product | Carousel | "40 browser tabs, or 1 Opportunity Web?" | Your mission at the center. Around it: Funders, Partners, Government, Resources, Readiness, Pathways. One picture instead of forty tabs. Swipe to see how the Opportunity Web works. → | Orb-web hero, pill nodes orbiting a gold "YOUR MISSION" hub; 6 zoom slides | "Map your web — join the pilot →" | anansiatlas.com/anansi-atlas/ | Save commenters to Leads tab | IG carousel (same slides) |
| Wed | LinkedIn | Marcus Scott | Educational | Text + image | "What's a 'readiness gap' — and why does it cost you grants?" | A readiness gap is the distance between what a funder expects and what your org can show today. Most nonprofits never see theirs until a rejection. The Snapshot surfaces readiness gaps *before* you apply — teal = strength, gold = gap. Fix the gap, then go after the money. | Snapshot readiness section; teal/gold coding | "Find your readiness gaps →" | anansiatlas.com/anansi-atlas/ | DM anyone who says "how?" | TikTok explainer |
| Thu | LinkedIn | Anansi Atlas | Proof/Pilot | Text post | "We're taking 20 founding nonprofits. Then the door closes at this price." | Founding Atlas Partners Pilot: $150/month, locked for life, for the first 20 mission-driven orgs. After that it's $299. No per-report fees, no usage limits, cancel anytime. You get the Opportunity Web Snapshot, a 45-min walkthrough, and full platform access. Spots are limited by design. | Navy "20 spots" counter card, gold accent | "Claim a founding spot →" | anansiatlas.com/anansi-atlas/ | Track applications in CRM tab | Pin as featured post |
| Fri | Instagram | Anansi Atlas | Category Vocab | Carousel | "Six things every nonprofit should be able to see about their mission." | Funders. Partners. Government. Resources. Readiness. Pathways. Most orgs track maybe two. Anansi Atlas maps all six around your mission. Which one are you flying blind on? | 6 gold-on-navy node cards, one per slide | "See all six →" | anansiatlas.com/anansi-atlas/ | Poll in Stories: "which node?" | LinkedIn document post |
| Sat | TikTok | Anansi Atlas | Problem | Reel/Short | "POV: the grant you needed closed last week and nobody told you." | Deadlines, funders, and partners live in a hundred places. By the time you find them, they're gone. Anansi Atlas puts the whole opportunity landscape in one view — with rose 'Due' pills so no deadline sneaks past you. | Screen-record the Snapshot deadline pills; fast cuts, navy/gold | "Stop missing deadlines →" | anansiatlas.com/anansi-atlas/ | Reply to comments with link | IG Reel repost |
| Mon | LinkedIn | Marcus Scott | Platform/Product | Video | "This is the 'Top Move Right Now' card. It tells you what to do today." | Most tools give you data and leave. The Dashboard gives you one next action: 'What To Do Next.' KPI health scores for Readiness, Partners, Pathways, Opportunities — then the single move that matters most this week. | Screen-record Dashboard "What To Do Next" + KPI scores | "See your next move →" | anansiatlas.com/anansi-atlas/ | Book walkthroughs from replies | TikTok + IG Reel |
| Tue | LinkedIn | Anansi Atlas | Educational | Text post | "Funder pathways vs. partner pathways — most orgs only chase one." | A funder pathway is a route to capital. A partner pathway is a route to capacity, credibility, and shared reach. Winning orgs work both. The Snapshot maps both around your mission and ranks the top opportunities on each. | Snapshot funder + partner pathways side by side | "Map both pathways →" | anansiatlas.com/anansi-atlas/ | DM "want a walkthrough?" | Carousel breakdown |
| Wed | Instagram | Anansi Atlas | Platform/Product | Reel/Short | "Watch a nonprofit's opportunity web build itself." | From scattered to focused in one screen. Your mission at the center, the web forming around it. This is the Opportunity Web. | Motion graphic: nodes animate into orbit around gold hub | "Build yours →" | anansiatlas.com/anansi-atlas/ | Save engaged accounts | TikTok repost |
| Thu | LinkedIn | Marcus Scott | Proof/Pilot | Text post | "What the Opportunity Web Snapshot actually shows you (not a grant list)." | It leads with a summary + a 30-day action plan. Then: funder pathways, partner pathways, top opportunities, readiness, risks & gaps. It's not a grant search — it's a map of the opportunity landscape around your mission, with the practical next steps. | Snapshot summary + 30-day action plan screenshot | "See a real Snapshot →" | anansiatlas.com/anansi-atlas/ | Offer walkthrough in DMs | Carousel |
| Fri | LinkedIn | Anansi Atlas | Category Vocab | Document post | "Government pathways: the opportunity most nonprofits skip." | Grants aren't the only route to capital. Government pathways — contracts, programs, designations — sit right next to funders on your Opportunity Web. Most orgs never map them. Here's why that's a mistake. | Government node highlighted on the web | "Map your government pathways →" | anansiatlas.com/anansi-atlas/ | DM local orgs | TikTok explainer |
| Sat | TikTok | Anansi Atlas | Problem | Reel/Short | "Your opportunity is scattered across 6 places. Here's all of them." | Websites. Funder portals. Emails. Spreadsheets. Relationships. Institutional memory. That's where your next opportunity is hiding. One tool pulls it into a single web. | Fast montage of the 6 chaos sources → collapse into the web | "Pull it together →" | anansiatlas.com/anansi-atlas/ | Link in bio + comments | IG Reel |
| Mon | LinkedIn | Marcus Scott | Educational | Text + image | "Strategic risk is the thing your board isn't asking about yet." | Funding is one risk. But over-reliance on one funder, a missed compliance window, a partner gap — those sink missions quietly. The Snapshot's risks & gaps section names them before they cost you. | Snapshot risks & gaps section; gold gap markers | "See your risks & gaps →" | anansiatlas.com/anansi-atlas/ | Book calls with EDs | Carousel |
| Tue | Instagram | Anansi Atlas | Proof/Pilot | Carousel | "$150/month. Locked for life. 20 spots." | The Founding Atlas Partners Pilot: founding rate $150/mo forever, first 20 orgs, then $299. Snapshot + 45-min walkthrough + full platform access included. No per-report fees. Cancel anytime. This is how you get in early. | Bold navy pricing card, gold "20 spots" | "Apply now →" | anansiatlas.com/anansi-atlas/ | Move applicants to CRM | LinkedIn post |
| Wed | LinkedIn | Anansi Atlas | Platform/Product | Carousel | "From scattered opportunity to focused action — in one snapshot." | Slide through the real Snapshot: summary, 30-day plan, funder pathways, partner pathways, top opportunities, readiness, risks. This is what 'seeing your web clearly' looks like. | 7 real Snapshot section screenshots, navy/gold | "Get your Snapshot in the pilot →" | anansiatlas.com/anansi-atlas/ | DM everyone who saves it | IG + TikTok cut-downs |
| Thu | LinkedIn | Marcus Scott | Problem | Text post | "You don't have a funding problem. You have a visibility problem." | The opportunity is already around your mission — you just can't see all of it at once. That's not a strategy failure, it's a map failure. Anansi Atlas is the map. | Simple navy card, gold key line | "See your map →" | anansiatlas.com/anansi-atlas/ | Reply + DM engaged EDs | Reel voiceover |
| Fri | TikTok | Anansi Atlas | Category Vocab | Reel/Short | "Funders. Partners. Government. Resources. Readiness. Pathways." | Say them out loud. These are the six nodes of your opportunity web. If you can't see all six, you're leaving opportunity on the table. Anansi Atlas maps every one around your mission. | Six words hit the screen one at a time over the orb-web | "Map all six →" | anansiatlas.com/anansi-atlas/ | Pin comment with link | IG Reel + LinkedIn |

---

## PART 3 — Measurement Plan

A simple dashboard a non-technical founder can keep in one Google Sheet. It answers one question every Friday: **are we on pace for 19–20 pilot signups?**

### The funnel we're measuring

`Impressions → Profile views → Link clicks → Comments/DMs → Pilot applications → Booked calls → Joined`

### Dashboard layout (one Google Sheet, three tabs)

**Tab 1 — Weekly Scoreboard** (the dashboard you actually look at). One row per week:

| Week | Impressions | Profile views | Link clicks | Comments | DMs started | Pilot applications | Booked calls | Joined (cumulative) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Wk 1 | | | | | | | | | |

**Tab 2 — Per-Post Log.** One row per post (Date, Platform, Pillar, Hook, Impressions, Link clicks, Comments, DMs). This tells you *which content* drives clicks — feed winners back into Part 1, Stage 11.

**Tab 3 — Leads/CRM.** One row per human: Name, Org, Source post, Stage (`New → Talking → Applied → Booked → Joined`), Last touch date, Conversion notes.

Optional: highlight the Weekly Scoreboard's "Joined (cumulative)" cell with a conditional-format bar — a visible progress bar toward 20.

### How to capture each metric

| Metric | Where it comes from | How (MVP) | How (scaled) |
|---|---|---|---|
| Impressions | LinkedIn post analytics, IG Insights, TikTok analytics | Type into Per-Post Log weekly | n8n pulls nightly into the DB |
| Profile views | LinkedIn "profile views" dashboard; IG Insights | Read the native number; log weekly | Same, automated |
| Link clicks | Buffer/Later click stats **or** a Bitly link | Use one Bitly for the signup link → read clicks | Bitly API → n8n |
| Comments | Native post view | Count weekly | Auto-pulled |
| DMs started | Your LinkedIn/IG inbox | Tally new conversations you started or received | Zapier logs inbound |
| Pilot applications | The signup page (anansiatlas.com/anansi-atlas/) | Count form submissions / new sign-ups | Zapier: submission → CRM row + Slack ping |
| Booked calls | Your calendar (the 45-min walkthrough) | Count walkthroughs booked | Calendar → CRM |
| Joined | Payment / pilot roster | Count paying founding orgs | Stripe/roster → dashboard |
| Conversion notes | Your memory of each call | Free text in the Leads tab | Same |

**Tip:** use a single Bitly (or Buffer's built-in tracking) for the signup link so link clicks are one clean number instead of guessing across platforms.

### Weekly review ritual (every Friday, 30 minutes)

1. **Fill the scoreboard (10 min).** Type the week's numbers into Tab 1 from native analytics.
2. **Find the winner and the dud (5 min).** In Tab 2, sort by link clicks. Top post → mark for repurpose (Part 2's `Repurpose option`). Bottom post → retire that hook/pillar.
3. **Work the pipeline (10 min).** In Tab 3, every lead not yet `Applied` gets one follow-up DM (Part 1, Stage 10). Move stages.
4. **Check the pace (5 min).** Compare "Joined (cumulative)" to the target line below. Ahead → keep the mix. Behind → post more Proof/Pilot content and send more DMs.

### Benchmarks & targets (pre-launch founder chasing 19–20 signups)

Assume a ~12-week push. These are *starting* targets to calibrate against, not guarantees — adjust after 2–3 weeks of real data.

| Funnel stage | Rough conversion assumption | Weekly target (early) | 12-week target |
|---|---|---|---|
| Impressions | — | 5,000–10,000 | 60,000–120,000 |
| Profile views | ~1–2% of impressions | 75–150 | ~1,000+ |
| Link clicks | ~1–2% of impressions | 50–150 | ~800–1,500 |
| Comments + DMs started | engagement signal | 15–30 | ~250 |
| Pilot applications | ~3–5% of link clicks | 3–5 | ~40 |
| Booked calls | ~50% of applications | 2–3 | ~20–25 |
| **Joined** | ~80% of booked calls | 1–2 | **19–20** |

**Reading the dashboard:**
- **Low impressions?** Posting frequency / hooks — problem is at the top. Post more, sharpen Stage 3 hooks.
- **Good impressions, low clicks?** Weak CTA or wrong pillar mix — add more Proof/Pilot and Platform posts.
- **Good clicks, low applications?** The signup page or offer clarity — tighten how the $150/locked-for-life pilot is framed in captions.
- **Good applications, low joined?** The walkthrough call — that's a sales-conversation fix, not a content fix.

Simplest possible health check each Friday: **you want ~2 booked walkthroughs per week.** Hit that consistently for 12 weeks and the cohort fills.

---

*Runs on free tiers. Master Table is the spine. Approval column is the only gate. One number to watch: booked walkthroughs per week.*
