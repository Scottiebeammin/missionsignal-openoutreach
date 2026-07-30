// Single source of truth for the automated pipeline:
// which ad/post uses which ElevenLabs voice, the VO script, the output audio file,
// and the date it should auto-build on — kept in sync with the "Voice Needed" column
// in 07-content-calendar-july-2026.md.
//
// Voices are resolved by NAME against your ElevenLabs account ("My Voices"),
// so the pipeline auto-pulls the right voice — no voice IDs to hardcode.
//
// kind: "remotion"       -> full ad composition exists in src/ads/*, scheduler renders the MP4.
// kind: "voiceover-only" -> no Remotion composition yet for this calendar post; the scheduler
//                           still auto-generates the MP3 (drop it into whatever tool cuts that
//                           day's talking-head/b-roll clip). Build a Remotion comp later to
//                           fully automate the video too.
// reuseAudioFrom: "<id>" -> this date needs no new VO; it re-cuts an earlier date's audio.

export const ADS = [
  {
    id: "PlatformShowcase",
    kind: "remotion",
    voice: "Christopher",
    audioOut: "showcase-vo.mp3",
    scheduledDate: "2026-07-08", // hero Platform Walkthrough drop
    script: [
      "Your next opportunity is already out there.",
      "It's just scattered — across funder portals, emails, spreadsheets, and relationships.",
      "Anansi Atlas maps the web of opportunity around your mission: funders, partners, government pathways, resources, and readiness.",
      "Your Opportunity Web Snapshot shows your strongest asset, your biggest gap, and the single highest-leverage move to make next.",
      "Anansi Atlas. Apply for a founding seat at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "PilotSignup",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "pilot-vo.mp3",
    scheduledDate: "2026-07-18", // Jackson full-VO animated offer card (Jul 16 is a text/graphic post, not video)
    script: [
      "Applications are open for the Founding Atlas Partners Pilot.",
      "We're selecting nineteen nonprofit and mission-driven organizations.",
      "Each partner receives a guided Opportunity Web Snapshot, a forty-five minute walkthrough, and the living platform.",
      "A hundred and fifty dollars a month, locked for life, for the first twenty organizations.",
      "Nineteen seats remain. Apply now at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    // THE LAUNCH FILM — "The Web of Opportunity" cinematic brand film (Scott's full brief:
    // 9 scenes, globe hero, gradient mesh, moody laptop, flip cards). oneOff. Voice: Christopher.
    id: "WebOfOpportunityFilm",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "web-of-opportunity-film-vo.mp3",
    script: [
      "Every mission is surrounded by opportunity.",
      "The challenge isn't that opportunities don't exist. They're scattered across dozens of places — making them difficult to see, prioritize, and act on before they're missed.",
      "When opportunity is fragmented, organizations miss funding, partnerships, and momentum. Not because they lack potential — but because they lack visibility.",
      "That's why we built Anansi Atlas. An opportunity intelligence platform designed to help mission-driven organizations see the full web of opportunity surrounding their mission.",
      "Instead of searching across dozens of disconnected sources, Anansi Atlas helps organizations understand their entire opportunity ecosystem in one place.",
      "See hidden connections, identify strategic relationships, and focus on the opportunities that matter most.",
      "Your Opportunity Web Snapshot turns all of it into a clear, thirty-day action plan.",
      "Now, we're inviting a limited number of organizations to become Founding Atlas Partners, and help shape the future of Anansi Atlas.",
      "Be among the first to map the web of opportunity surrounding your mission. Join today, while seats remain.",
    ],
  },
  {
    // THE EXECUTIVE VISION FILM — "The Whole Field". Orange County FL government +
    // Central Florida grantmakers. 18 scenes, five acts, ~6:15. oneOff. Voice: Christopher.
    //
    // Generate with `node scripts/gen-vo-timestamped.mjs AnansiVisionFilm` (NOT `npm run vo`) —
    // the film has three long silent passages, so it needs the alignment JSON to slice the
    // master MP3 per line rather than laying one continuous track across the timeline.
    //
    // Scene 01 is silent by design and has no line here; the array starts at Scene 02.
    //
    // CTA (Scott, 2026-07-29): a SOFT close — "call or visit our website to learn more",
    // carrying the phone number and URL on screen. Deliberately still NO price and no seat
    // count: "$150 locked for life" cannot share the frame with "we're not here to sell you
    // software." So this partially breaks the every-ad checklist in BRAND-TEMPLATE.md §5
    // beat 6 — invitation, not conversion. See the BRAND-DEVIATION note in the film file.
    //
    // The partner line says "Empowered Girls" (no "Inc.") — TTS reads "Inc." as "ink",
    // and the spoken-out "Incorporated" sounded stiff. On screen it renders the full
    // legal "Empowered Girls Inc." Facts drawn from seed_egi.py: 501(c)(3), Orlando,
    // girls ages 9-18. Their impact figures (43 girls, $11k scholarships, 5,000
    // families) are deliberately NOT in the film — a specific claim about a partner
    // needs that partner's sign-off, not ours.
    id: "AnansiVisionFilm",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-vision-film-vo.mp3",
    script: [
      "Every community already holds what it needs. The people. The institutions. The money. In Orange County, Florida, all of it is here right now. That has never really been the question. The question is quieter, and harder: can the organizations closest to the work actually see it?",
      "A youth program in Pine Hills. A food pantry in Apopka. A workforce nonprofit two blocks from a foundation that funds exactly the kind of work they do — and neither one has any idea the other exists. Not because anyone failed. Because nobody ever drew the map.",
      "Every mission has more opportunities than it can see. That is not a criticism. It's just true, everywhere, all the time.",
      "The opportunity already exists. It's just scattered. So we went looking for it.",
      "So we built the count. Three hundred and ten thousand I.R.S. returns, read line by line. Three hundred twenty-six thousand grant records relevant to Florida. From those, thirteen thousand five hundred fifty-four verified funders. And one hundred fourteen thousand exempt organizations in the Florida database — the full field, not a sample of it.",
      "Then we pointed it at one real organization here in Orange County. What came back was sixty-three point six million dollars in verified foundation grants, going to four hundred seventy-four Orange County organizations. One thousand nine hundred and twelve individual grants. Every one of them traceable back to a filing you can open yourself.",
      "That last part matters more than the number. Every opportunity carries a real source, or it never enters the system at all. Verified, or verify-first. There is no third category.",
      "Funders. Partners. Government. Resources. Readiness. Pathways. This is what we mean by a web.",
      "Here is the platform, at the pace you'd actually use it on a Tuesday morning. A mission sits at the center of the screen. Around it, the funders. The partners. The government pathways. The resources. And an honest read on how ready that organization is to compete for any of it — including where it isn't.",
      "Nothing here was invented. Every node is drawn from public filings, public notices, and public records — the same information anyone could gather, if anyone had ten thousand hours. What the platform does is hold it all in one shape, so a single person can look at the whole thing at once.",
      "Watch one control. Sort by peer size. The top of the list stops being a five-million-dollar gift to a university, and becomes twenty-five-thousand-dollar grants to organizations the same size, in the same county, doing the same work. Nothing was added. Nothing was removed. The lens changed — and suddenly the list is about you.",
      "That's the whole idea. We don't get anyone funded. We don't promise a dollar. We map what is already there — and we show you where to look.",
      "Now — everything after this line is unbuilt. Not a beta. Not a roadmap promise. It's a question we'd like to ask out loud, in a room like this one.",
      "What if a funder could see the same map from the other side? Not who applied this cycle — who is actually out there. Which organizations in a county are doing the work, at what scale, with what capacity. And where a portfolio has a hole in it that nobody has named yet.",
      "What if a county could look at one sector — youth development, housing, workforce — and see the entire field at once? Where the dollars land. Where they don't. Who is carrying weight without support. None of that exists today. We're showing it to you in wireframe, on purpose, because whether it should exist isn't ours to decide alone.",
      "What does exist is this. Empowered Girls, right here in Orange County, works with girls ages nine to eighteen — and today they are live in production as our first founding partner. One organization is not a movement. It is, however, a beginning.",
      "So we're not here to sell you software. We're here to ask a question. Whether the way this county sees its own nonprofit sector could be clearer than it is today. Whether the organizations already doing the work deserve to see the whole field they're standing in. We think they do. Reveal. Connect. Clarify. Empower. Act. Anansi Atlas. See the whole web. Call us, or visit anansiatlas.com, to learn more.",
    ],
  },
  {
    // FIRST LINKEDIN POST — "19 of 20 Seats" stat reveal. oneOff (posted manually, not
    // scheduler-dated). Voice: Jackson (assertive/scarcity — same as PilotSignup).
    id: "PilotSeatsReveal",
    kind: "remotion",
    oneOff: true,
    voice: "Jackson",
    audioOut: "pilot-seats-reveal-vo.mp3",
    script: [
      "Founding Atlas Partners applications are open.",
      "Nineteen of twenty seats are already claimed — just one spot left before the rate closes for good.",
      "One hundred fifty dollars a month, locked in for life.",
      "Apply now, before the founding cohort closes.",
    ],
  },
  {
    id: "Jul10-SnapshotClip",
    kind: "remotion",
    voice: "Siren",
    audioOut: "jul10-siren.mp3",
    scheduledDate: "2026-07-10", // optional screen b-roll under the Fri Jul 10 talking-head short
    script: [
      "The Opportunity Web Snapshot leads with a summary and a 30-day action plan — not a search result.",
      "That's the difference between information and direction.",
    ],
  },
  {
    id: "Jul11-Repurpose",
    kind: "voiceover-only",
    reuseAudioFrom: "PlatformShowcase", // re-cut of the Jul 8 walkthrough — no new VO to generate
    scheduledDate: "2026-07-11",
  },
  {
    id: "Jul17-EndorsementOutro",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "jul17-jackson.mp3",
    scheduledDate: "2026-07-17", // optional outro line on the founder endorsement video's closing card
    script: [
      "Founding Partners lock in one hundred and fifty dollars a month, for life.",
      "Apply at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "Jul24-ListVsMap",
    kind: "remotion",
    voice: "Siren",
    audioOut: "jul24-siren.mp3",
    scheduledDate: "2026-07-24", // screen segment for the "list vs. map" split-screen short
    script: [
      "One page. One clear move.",
      "Funders, partners, and government pathways — mapped around your mission, with readiness scored and a single top move to make next.",
    ],
  },
  {
    id: "Jul25-SnapshotScroll",
    kind: "remotion",
    voice: "Giselle",
    audioOut: "jul25-giselle.mp3",
    scheduledDate: "2026-07-25", // full VO for the Snapshot scroll-through repurpose
    script: [
      "Your Snapshot doesn't bury the point. It opens with a 30-day action plan, ranked for your mission.",
      "Teal marks strength. Gold marks a gap. One page. One clear move.",
      "Included in the founding pilot.",
    ],
  },
  {
    id: "Jul31-ClosingOutro",
    kind: "remotion",
    voice: "Jackson",
    audioOut: "jul31-jackson.mp3",
    scheduledDate: "2026-07-31", // optional outro line on the founder closing video's card
    script: [
      "The Founding Atlas Partners pilot is nearly full.",
      "One hundred and fifty dollars a month, locked for life. Apply or message me today.",
    ],
  },

  // ── One-off flagship commercials (no scheduledDate → the scheduler ignores them;
  //    `npm run vo` still generates their narration, `npm run build` renders them). ──
  {
    id: "PremiumShowcase",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "premium-showcase-vo.mp3",
    script: [
      "Every mission is surrounded by opportunity.",
      "The problem was never opportunity. It was visibility.",
      "This is Anansi Atlas.",
      "Your Dashboard opens with one clear next move.",
      "Your Opportunity Web maps your mission at the center.",
      "Your Snapshot opens with a 30-day action plan.",
      "Founding Atlas Partners aren't just customers. They're the first twenty organizations shaping this platform — a rate locked in for life.",
      "If you're ready to stop guessing, join the family.",
      "Apply at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    id: "ProductWalkthrough",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "product-walkthrough-vo.mp3", // "From Scattered Opportunity to Focused Action" (~90s, flowing narration)
    script: [
      "Every nonprofit is surrounded by opportunities — funders who'd say yes, partners who'd open doors, public dollars already earmarked for work like yours.",
      "The hard part was never that opportunity didn't exist. It's that it was scattered — across browser tabs, spreadsheets, and inboxes, with no one quite sure what to chase first.",
      "Anansi Atlas changes that. You start by telling us about your mission — who you serve, and what you're building. From there, the platform maps the entire web of opportunity around it.",
      "Your Opportunity Web Snapshot opens with a clear, thirty-day action plan, ranked specifically for your mission.",
      "Scroll deeper, and you'll find the funders who are actually aligned with your work, the partners who make your applications stronger, and the local government pathways most teams never have time to uncover.",
      "We surface the community resources that build your capacity, and score your readiness honestly, so you know exactly where you're strong, and where there's a gap to close.",
      "Every risk that could slow you down gets flagged early, and every opportunity worth pursuing moves into a living pipeline — carried from first spotted, all the way to won.",
      "The result is simple. Instead of chasing scattered leads, your team always knows exactly where to focus next.",
      "We're opening the Founding Atlas Partners Pilot to nineteen to twenty mission-driven organizations.",
      "Apply today at anansi atlas dot com, slash anansi atlas.",
    ],
  },
  {
    // STANDALONE FLAGSHIP — "Who We Are + Platform Walkthrough" cold-outreach video. Scott's
    // final approved script (verbatim — do not paraphrase). Use case: cold outreach. Tone:
    // premium, calm, strategic, mission-centered. Same laptop-mockup/logo style as the Jul 8
    // hero; rendered in both square (LinkedIn) and wide (YouTube) cuts. Voice: Giselle.
    // NOTE: at natural TTS pace this script runs longer than the "60-75s" noted in Scott's brief
    // — used verbatim per his "use this script" instruction. Revised per Scott's "fix it" pass
    // (2026-07-04 conversion review): sharper cold-open hook, one line pulled forward to make the
    // demo-org screenshots feel like "picture your own mission" instead of someone else's data,
    // the two negation lines consolidated into one tighter beat, and price/scarcity added to the
    // close (previously the CTA never stated $150/mo or the seat count — the single biggest
    // missing conversion lever). Re-run scripts/gen-vo-timestamped.mjs after any further edits.
    id: "WhoWeAreWalkthrough",
    kind: "remotion",
    oneOff: true,
    voice: "Giselle",
    audioOut: "who-we-are-walkthrough-vo.mp3",
    script: [
      // [Opening — Brand Belief]
      "Somewhere right now, a funder is aligned with your mission — and you don't know it exists.",
      "Funders. Partners. Resources. Government pathways. Relationships. Risks. Next steps.",
      "The challenge is that most of that opportunity is scattered — across websites, portals, conversations, spreadsheets, deadlines, and institutional knowledge.",
      "So even strong organizations can miss what is already connected to their mission.",
      "That is the problem Anansi Atlas is built to solve.",
      // [Product Reveal]
      "Anansi Atlas helps mission-driven organizations map the web of opportunity around their mission.",
      "Not a generic list. Not another database to search through.",
      "But a clearer way to see the funders, partners, resources, pathways, readiness gaps, risks, and next steps that may matter most.",
      // [Walkthrough Bridge]
      "Here is what that looks like inside the platform — picture this mapped to your own mission.",
      // [Dashboard]
      "The dashboard begins with focus.",
      "What to do next. Readiness signals. Relationship opportunities. Pathway health.",
      "A clearer view of where your organization stands — and where it can move next.",
      // [Opportunity Web]
      "The Opportunity Web places your mission at the center.",
      "Around it, Anansi Atlas organizes the opportunities and connections surrounding your work — funders, partners, government pathways, resources, risks, and practical next steps.",
      // [Opportunity Web Snapshot]
      "The Opportunity Web Snapshot turns that map into action.",
      "It gives your team a mission-centered brief with aligned opportunities, readiness insights, and a practical 30-day action plan.",
      "So instead of chasing scattered leads, your organization can move with more clarity and focus.",
      // [Closing CTA]
      "This is Anansi Atlas.",
      "The Web of Opportunity, mapped around your mission.",
      "We're currently inviting a limited group of mission-driven organizations to the Founding Atlas Partners Pilot — $150 a month, locked for life, while founding seats remain.",
      "Apply at anansiatlas.com.",
    ],
  },
  {
    // JULY CONTENT CALENDAR — Wed Jul 8 hero "Platform Walkthrough" (content-center/07-content-
    // calendar-july-2026.md). The month's highest-visibility product-proof asset: Dashboard ->
    // Opportunity Web -> Snapshot, real screenshots, ends on the founding-seat CTA. Voice:
    // Giselle (per Scott — calendar draft said Christopher, overridden to a female voice).
    id: "Jul08-PlatformWalkthrough",
    kind: "remotion",
    oneOff: true,
    voice: "Giselle",
    audioOut: "jul08-platform-walkthrough-vo.mp3",
    script: [
      "Let me show you the actual product. Not a mockup — the thing you'd use every day.",
      "This is Anansi Atlas. Sign in, and your Dashboard opens with one card: What To Do Next, plus your readiness, relationship, and pathway health at a glance.",
      "The Opportunity Web puts your mission at the center — funders, partners, government, resources, readiness, and pathways, orbiting it, so you see the whole landscape at once.",
      "And your Snapshot leads with a 30-day action plan, ranked for your mission — not a wall of grants.",
      "No pitch deck. This is the working software founding partners log into on day one.",
      "Want the full walkthrough with your own data? It comes with your founding seat. Apply at anansiatlas.com.",
    ],
  },
  {
    // ONBOARDING TUTORIAL — "Getting Started with Anansi Atlas" (profile creation -> dashboard
    // tour). Instructional, not a sales piece: no pilot CTA/pricing. Voice: Giselle (the
    // calmer, explainer-toned female voice already used for Jul25-SnapshotScroll).
    id: "DashboardWalkthrough",
    kind: "remotion",
    oneOff: true,
    voice: "Giselle",
    audioOut: "dashboard-walkthrough-vo.mp3",
    script: [
      "Welcome to Anansi Atlas. Sign in, and let's take a tour — from setting up your profile to understanding your dashboard.",
      "First, tell us about your organization — your mission, your programs, and where you work. Atlas builds your profile from there.",
      "Home is your daily base: one clear next move, your health scores, and upcoming deadlines, readable in under a minute.",
      "Snapshot is your executive brief: the summary, your Opportunity Web map, and a 30-day action plan, together in one place.",
      "Ecosystem maps everything around your mission: funding, government, resources, partnerships, and relationships, as tabs of one view.",
      "Opportunities is where you decide. Top picks first, all matches and discovery behind tabs. Track anything worth pursuing.",
      "Pipeline is your lifecycle board: everything you committed to, from discovered to awarded, with deadlines flagged.",
      "Readiness shows what stands between you and a competitive application, with documents and evidence one tab away.",
      "And Organization is home for your profile, your wins, and your membership. Keep it fresh; everything else in the Atlas is built from it.",
      "That's the tour, start to finish. You know your way around — come back anytime at anansiatlas.com.",
    ],
  },
  {
    id: "FullExplainer",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "full-explainer-vo.mp3",
    script: [
      "What if the funders, partners, and public dollars already aligned with your mission weren't hiding — they were just never mapped?",
      "Most nonprofit teams do this work in forty browser tabs. A funder database here. An email thread there. A spreadsheet somebody built two years ago that only one person still understands. Deadlines get missed. Warm partners go uncontacted. It's not a lack of effort. It's a lack of a system built to hold all of it in one place.",
      "This is Anansi Atlas — a nonprofit opportunity intelligence platform. We call it the Web of Opportunity, because every mission sits at the center of one: aligned funders, potential partners, government pathways, and community resources, all already there, waiting to be seen clearly enough to act on.",
      "Here's what that looks like in practice. Your Dashboard is home base. It opens with a single card: What To Do Next — one highest-leverage action, not a to-do list. Around it, health scores for Readiness, Partners, Pathways, and Opportunities. Upcoming deadlines are flagged before they're urgent. A busy executive director can open this for sixty seconds each morning and know exactly where to spend the day.",
      "Click into the Opportunity Web, and you'll see your mission at the center — literally. Six nodes orbit it: Funders, Partners, Government, Resources, Readiness, and Pathways. This is the actual shape of your opportunity landscape, mapped instead of scattered. Nothing here is guesswork. It's built from real research on your mission.",
      "Your Opportunity Web Snapshot is the executive brief. It opens with a plain-language summary and a thirty-day action plan, ranked specifically for your mission — not a wall of grants with no context. Below that: your top funder and partner pathways, ranked by fit. Your Readiness, scored honestly — teal where you're strong, gold where there's a gap. And your Risks and Gaps, so you see what could slow you down before it costs you a quarter. A list tells you what exists. A Snapshot tells you what to do next, in order, starting today.",
      "When an opportunity is worth pursuing, it moves into your Pipeline — a living board that carries it from spotted to submitted to won. Partners and Sponsorship maps the funders and organizations already aligned with your mission. And Resources surfaces the capacity-building, technology, and volunteer support that strengthens your readiness before you ever apply.",
      "We built Anansi Atlas because we believe mission-driven work shouldn't lose to logistics. The opportunity around your mission was never the problem. Seeing it clearly, and knowing what to do about it first, was. That's what this platform gives you back — time, clarity, and a system that keeps working even on the weeks you don't have time to look.",
      "We're opening the Founding Atlas Partners Pilot to twenty mission-driven organizations — a rate locked in for life, a Snapshot built around your actual mission, and a personal walkthrough with our team. If this is the system your organization has been missing, don't wait for the standard rate. Register now at anansi atlas dot com, slash anansi atlas, and let's map your web of opportunity today.",
    ],
  },
];

// ElevenLabs voice settings (tuned for an awake, credible business read — not sleepy).
export const VOICE_SETTINGS = {
  model_id: "eleven_multilingual_v2",
  voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true },
};
