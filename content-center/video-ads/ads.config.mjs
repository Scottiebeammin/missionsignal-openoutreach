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
      "Every community already holds what it needs. The people. The institutions. The opportunity. In Orange County, Florida, all of it is here right now. That has never really been the question. The question is quieter, and harder: can the organizations closest to the work actually see it?",
      "A youth program in Pine Hills. A food pantry in Apopka. A workforce nonprofit two blocks from a foundation that funds exactly the kind of work they do — and neither one has any idea the other exists. Not because anyone failed. Because nobody ever drew the map.",
      "Every mission has more opportunities than it can see. That is not a criticism. It's just true, everywhere, all the time.",
      "The opportunity already exists. It's just scattered. So we went looking for it.",
      "So we built the count. Three hundred and ten thousand I.R.S. returns, read line by line. Three hundred twenty-six thousand grant records relevant to Florida. From those, thirteen thousand five hundred fifty-four verified funders. And one hundred fourteen thousand exempt organizations in the Florida database — the full field, not a sample of it.",
      "Then we pointed it at Orange County itself. What came back was sixty-three point six million dollars in verified foundation grants, reaching four hundred seventy-four organizations across this county. One thousand nine hundred and twelve individual grants. Every one of them traceable back to a filing you can open yourself.",
      "That last part matters more than the number. Every opportunity carries a real source, or it never enters the system at all. Verified, or verify-first. There is no third category.",
      "Funders. Partners. Government. Resources. Readiness. Pathways. This is what we mean by a web.",
      "Here is the platform, at the pace you'd actually use it on a Tuesday morning. A mission sits at the center of the screen. Around it, the funders. The partners. The government pathways. The resources. And an honest read on how ready that organization is to compete for any of it — including where it isn't.",
      "Nothing here was invented. Every node is drawn from public filings, public notices, and public records — the same information anyone could gather, if anyone had ten thousand hours. What the platform does is hold it all in one shape, so a single person can look at the whole thing at once.",
      "Watch one control. Sort by peer size. The top of the list stops being a million-dollar research grant to a university, and becomes twenty-five-thousand-dollar grants to organizations the same size, in the same county, doing the same work. Nothing was added. Nothing was removed. The lens changed — and suddenly the list is about you.",
      "That's the whole idea. We don't get anyone funded. We don't promise a dollar. We map what is already there — and we show you where to look. That's Anansi Atlas.",
      "Now — everything after this line is unbuilt. Not a beta. Not a roadmap promise. It's a question we'd like to ask out loud, in a room like this one.",
      "Imagine a funder could see the same map. Not just who applied this cycle — the full lifecycle of every managed grant. One place for communication with every award winner. A central hub for your grant data. Every grant, and every awardee, seen at once.",
      "What if a county could look at one sector — youth development, housing, workforce — and see the entire field at once? Where the dollars land. Where they don't. Who is carrying weight without support. None of that exists today. We're showing it to you in wireframe, on purpose, because whether it should exist isn't ours to decide alone.",
      "What does exist is this. Empowered Girls, right here in Orange County, works with girls ages nine to eighteen — and today they are live in production as our first founding partner. One organization is not a movement. It is, however, a beginning.",
      "So we're not here to sell you software. We're here to ask a question. Whether the way this county sees its own nonprofit sector could be clearer than it is today. Whether the organizations already doing the work deserve to see the whole field they're standing in. We think they do. Reveal. Connect. Clarify. Empower. Act. Anansi Atlas. See the whole web. Call us, or visit anansiatlas.com, to learn more.",
    ],
  },
  {
    // THE BOARD FILM — "The Ceiling Isn't This Room". Black Architects in the Making
    // (BAM) Orlando. 18 scenes, five acts, ~5:55. oneOff. Voice: Christopher.
    //
    // Generate with `node scripts/gen-vo-timestamped.mjs BamOrlandoFilm` (NOT `npm run vo`) —
    // same reason as AnansiVisionFilm: the film has silent passages and needs the
    // alignment JSON to slice the master MP3 per line.
    //
    // Scene 01 is silent by design and has no line here; the array starts at Scene 02.
    //
    // ⚠️ NOT A PUBLIC ASSET. Act IV shows BAM's OWN workspace (project 18), not the
    // Creative Display demo profile the public ads use. That is deliberate — the whole
    // pitch is "this already exists and it's yours" — but it means this film is for
    // the BAM board only. Do not post it to LinkedIn/YouTube.
    //
    // Every figure traces to src/data/bamOrlandoFacts.ts, which sources them to
    // bamorlando.org, their LinkedIn, and IRS 990-PF filings for Orange County.
    // The $20.6M / 229 / 994 trio is corroborated on screen by their own dashboard.
    // Deliberately NOT narrated: the dashboard's "418 opportunities mapped" and "317
    // strong matches" — those are computed against reference tables, not stored
    // matched records, and the same screen reads "0 verified grants matched to you".
    // Claiming 418 in the VO while a 0 sits on screen loses the room.
    // VOCABULARY (Scott, 2026-07-30): this film never says "money". The brand word
    // is opportunity — "The opportunity exists", "the opportunity stays exactly
    // where it has always been". Sc07's question became "who actually gives to an
    // organization like yours" rather than forcing the noun in a third time.
    // Dollar AMOUNTS stay ($56.0M, $20.6M, $5,000, $150/month, $29,480): those are
    // the receipts the whole film rests on, and they are not the word "money".
    id: "BamOrlandoFilm",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "bam-orlando-film-vo.mp3",
    script: [
      "This is Black Architects in the Making. The Orlando chapter. Founded in twenty eighteen, and run on volunteers every day since. You take students of color into architecture firms, into design studios, into real buildings — and you show them a career nobody ever told them was theirs.",
      "Three hundred students since you started. A hundred and thirty-five this year alone. Fourteen workshops. Eighty-seven volunteers. Twenty-nine thousand, four hundred and eighty dollars raised last year — and every dollar of it came from your own community.",
      "None of that came from a form I asked you to fill out. I built this from your website, your public tax filings, and the record you have already made in this county. Nothing you are about to see is a guess.",
      "So you already know the problem. You are doing the work. The opportunity exists. But finding out who actually funds architecture pathways for students of color in Orange County means nights of searching, after the workshops, after the day job — and you do not have a grant writer.",
      "So the opportunity stays exactly where it has always been. Not missing. Invisible. That distinction is the entire reason this exists.",
      "So we built the count. Three hundred and ten thousand I.R.S. returns, read line by line. Three hundred twenty-six thousand grant records relevant to Florida. Thirteen thousand five hundred fifty-four verified funders. Then we pointed all of it at one question: who actually gives to an organization like yours, in your county?",
      "Fifty-six million dollars flowed into Orange County nonprofits. Six hundred and fifty-three foundations. Two thousand six hundred and twenty-two grants, every one of them off a filing. That is the pool.",
      "Twenty point six million of that went to organizations your size. Two hundred and twenty-nine foundations. Nine hundred and ninety-four grants. Not the whole ocean — the part of it you can actually swim in. That is your lane.",
      "And the typical grant to an organization your size is five thousand dollars. Not a projection. Not an average of averages. It is the number that shows up, over and over, on the filings. That is your first check.",
      "Here is what that looks like with the names left in. Black History Project — five thousand. Love Our Youth — five thousand. Page Fifteen — five thousand. Lakemont Elementary P.T.O. Orlando Athletic Training Academy. Pop Warner. Real organizations. Your size. Your county. Getting real checks.",
      "And this is not a mockup. This is your workspace, already built, already sitting there. Twenty point six million dollars in verified foundation grants, to two hundred and twenty-nine organizations like yours. That line is not marketing copy. It is a query, and you can run it yourself.",
      "Your mission sits in the middle. Around it, six things: funders, partners, government pathways, resources, readiness, and the pathways that connect them. That is what we mean by a web. Not a list you scroll. A landscape you can see all at once.",
      "Now watch one control. Sorted the ordinary way, the top of the list is a million-dollar research grant to the University of Florida. Sort by organizations your size, and the very same data returns five-thousand-dollar checks to Orlando nonprofits doing your kind of work. Nothing was added. Nothing was removed. The lens changed.",
      "And it tells you the truth about where you stand. Sixty-one out of a hundred. Developing. Programs need clearer definition — that is your top gap. Missing documents in the vault — that is your highest-leverage fix. A tool that only flatters you is not worth having.",
      "So, plainly, three things this will not do. It will not call a three hundred and fifty million dollar university an organization like you. It will not show you a grant you cannot click through and verify against the filing. And it will not promise to get you funded. You still write the ask. Verified means verified.",
      "A hundred and fifty dollars a month. Founding rate, locked for life, as one of the first twenty partners. That is the whole offer. No setup fee. No annual contract. No percentage of anything you raise. If the map is wrong, you will know inside a month.",
      "And what I built for Orlando is not Orlando-specific. The same map exists for Broward. The same map exists for Miami. Every chapter, the same three numbers, the same receipts. The ceiling is not this room. Anansi Atlas. See the whole web. Let's start with Orlando.",
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
  {
    // CAMPAIGN VIDEO 1 — Universal Anansi Atlas Commercial (~90s). National audience;
    // deliberately NO Empowered Girls, NO county figures — must work for any US nonprofit.
    // Generate with `node scripts/gen-vo-timestamped.mjs AnansiUniversalCommercial` —
    // logo open (S01) and end card (S10) are silent, so the film slices the master per line.
    // Script source: Scott's master campaign prompt 2026-07-31, conformed to brand voice.
    id: "AnansiUniversalCommercial",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-universal-commercial-vo.mp3",
    script: [
      "You are already doing the work. But the opportunities surrounding your mission are scattered everywhere.",
      "Every organization operates inside a larger opportunity ecosystem — funders, partners, government pathways, community resources, risks, and next steps.",
      "The problem is not always finding another opportunity. It is understanding how everything connects — and knowing what your organization is ready to pursue.",
      "Anansi Atlas turns that scattered information into one clear view of the opportunity web surrounding your mission.",
      "Your profile is built around your mission, your location, the people you serve, your goals, and your current capacity.",
      "You receive more than a list. You see where to focus, who could help, what may be holding you back, and what to do next.",
      "Whether you serve one neighborhood, an entire state, or communities across the country, your opportunity web is unique.",
      "Your mission is already surrounded by opportunity. Anansi Atlas helps you see the whole web — and decide what to do next.",
    ],
  },
  {
    // CAMPAIGN VIDEO 2 — 30-second social ad, native 9:16. Lines 1-5 are the master cut
    // (hook A body); lines 6-8 are alternate hooks B/C/D voiced in the same take so every
    // variant shares one master. Generate with
    // `node scripts/gen-vo-timestamped.mjs AnansiSocial30`.
    id: "AnansiSocial30",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-social30-vo.mp3",
    script: [
      "Your nonprofit may not have an opportunity problem.",
      "You may have a visibility problem.",
      "Anansi Atlas maps the funders, partners, resources, government pathways, and readiness gaps surrounding your mission.",
      "Then it turns that research into clear priorities, and a practical thirty-day action plan.",
      "See your whole web of opportunity.",
      "What opportunities are hiding around your mission?",
      "Grants are only one part of your opportunity web.",
      "Your next opportunity may already be connected to your mission.",
    ],
  },
  {
    // CAMPAIGN VARIATION — Universal commercial A, "The Visibility Problem" (~70s).
    // Confusion → visibility → clarity → action. Same claims, different strategy.
    id: "AnansiUniversalVisibility",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-universal-visibility-vo.mp3",
    script: [
      "Your organization may not have an opportunity problem. It may have a visibility problem.",
      "The funders, the partners, the public programs, the community resources — most of it is already out there. But it lives in forty browser tabs, six spreadsheets, and somebody's inbox.",
      "And when you can't see how it all connects, every decision gets harder than it should be.",
      "Anansi Atlas brings the whole ecosystem into view — one connected map of the opportunity web around your mission.",
      "Watch what happens when scattered research becomes structure. Funding pathways. Strategic partners. Government programs. An honest read on your readiness.",
      "Complexity in. Clarity out. And a practical plan for what to do next.",
      "The opportunity may already exist. Anansi Atlas helps you see how it connects.",
    ],
  },
  {
    // CAMPAIGN VARIATION — Universal commercial B, "Imagine Your Organization Here" (~70s).
    // Curiosity → personalization → possibility → action. Laptop-first structure.
    id: "AnansiUniversalImagine",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-universal-imagine-vo.mp3",
    script: [
      "Imagine seeing the full opportunity ecosystem surrounding your organization — in one clear view.",
      "It starts with what makes you, you. Your mission. Your location. The people you serve. Your goals. Your current capacity.",
      "Anansi Atlas builds your profile around those answers. Not a template. Never the same twice.",
      "Change the mission, and the web changes with it. Change the geography, and new pathways appear.",
      "A youth program serving one county. A housing nonprofit working statewide. An arts organization in three cities. Each one sees a different web — because each one is different.",
      "What you receive is a working map. Funders. Partners. Public programs. Resources. Readiness. And a thirty-day plan to act on it.",
      "Your mission. Your location. Your opportunity web.",
    ],
  },
  {
    // CAMPAIGN VARIATIONS — social 30s A ("Grants are only one part", lines 1-4) and
    // B ("Your Organization Here", lines 5-8), one master take.
    id: "AnansiSocial30Vars",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "anansi-social30-vars-vo.mp3",
    script: [
      "Grants are only one part of your opportunity web.",
      "Around your mission are potential partners, government pathways, community resources, funders, risks, and next steps.",
      "Anansi Atlas brings those connections into one clear opportunity profile — built around your organization.",
      "See your whole web of opportunity.",
      "What would Anansi Atlas reveal around your mission?",
      "Potential funders. Strategic partners. Government pathways. Community resources. Readiness gaps. And a practical plan for what to do next.",
      "Built around your mission, your location, and your current capacity.",
      "Your organization could be here.",
    ],
  },
  {
    // CAMPAIGN VIDEO 3 — Empowered Girls Orlando/Orange County Research Film (~5:40).
    // EVERY factual claim traces to ANANSI_ATLAS_VIDEO_CAMPAIGN/14_SOURCE_LOG/.
    // EGI identity verified (Sunbiz N18000012567, EIN 83-2591882, empoweredgirlsinc.org);
    // mission line quotes their official site. Impact figures (43+ girls, 5,000
    // families) deliberately EXCLUDED per Scott 2026-07-29 — partner claims need
    // partner sign-off. Funders/partners/gov framed strictly as "potentially
    // aligned / eligibility to be confirmed". Readiness = categories the platform
    // reads, never claimed EGI weaknesses. Scene 01 title is silent.
    id: "EmpoweredGirlsResearchFilm",
    kind: "remotion",
    oneOff: true,
    voice: "Christopher",
    audioOut: "egi-research-film-vo.mp3",
    script: [
      "In Orlando, Florida, there is an organization that believes every girl deserves to grow into a confident, capable woman. Empowered Girls, founded in twenty eighteen, works with girls across Orange County through life skills, mentorship, health and wellness, and academics infused with empowerment.",
      "Their mission, in their own words: empowering girls to grow into confident, capable women through life skills, mentorship, and programs that help them overcome barriers and achieve success.",
      "The work happens in a county of real scale. Orange County is home to more than three hundred twenty-two thousand children — about one in five residents. And about one in six of those children lives below the poverty line.",
      "Nationally, the picture for girls is just as urgent. By fifth grade, only sixty-eight percent of girls describe themselves as confident — down from eighty-six percent six years earlier. And by one national estimate, one in three young people reach adulthood without ever having a mentor. This is the field Empowered Girls stands in.",
      "But no mission exists in isolation. Around this work is a larger ecosystem — funders, schools, government programs, community organizations, businesses, and people — who may already be aligned with what Empowered Girls is building. Anansi Atlas exists to map exactly that.",
      "Start with funding. In Central Florida, the pathways potentially aligned with girls' youth development are real and specific. A community foundation whose grassroots grants name youth development as a priority. A local charity with a microgrant program built for smaller organizations. And corporate giving from the region's largest employers, with youth and education programs that accept applications year-round.",
      "None of these are commitments. Every one is a doorway — worth researching, worth confirming, worth a conversation.",
      "Then, partners. Orange County Public Schools runs a formal Partners in Education program — the front door for organizations that work inside schools. The University of Central Florida connects student volunteers to more than two hundred community agencies. And Rollins College runs an institute whose entire purpose is strengthening Orange County nonprofits.",
      "Government has doorways of its own. Orange County's Citizens' Commission for Children reviews funding for youth-serving nonprofits every year. Community Development Block Grants support programs for families who need them most. And the City of Orlando builds neighborhood initiatives through nonprofit partners. Possible pathways — each with its own eligibility to confirm.",
      "And alongside opportunity, an honest look inward. The platform reads readiness the way a funder would — program documentation, outcome tracking, partnership materials — and shows where an organization is strong, and where to strengthen next. Not as criticism. As preparation.",
      "All of it comes together here. This is Empowered Girls' actual workspace in Anansi Atlas — live in production today. Their mission at the center. Around it, the funders. The partners. The government pathways. The resources. The readiness.",
      "From here, research becomes decisions. What to pursue. Who to call. What to prepare. In order, starting now.",
      "It ends in a plan — a thirty-day sequence of clear next actions. Confirm eligibility for the strongest funding pathways. Open the school partnership conversation. Assemble the readiness documents that outreach will ask for. Small steps, in the right order.",
      "This is the web surrounding Empowered Girls — built around their mission, their location, the girls they serve, their priorities, and their capacity today. Every organization's web looks different. That is the point. Anansi Atlas helps nonprofit leaders see what surrounds their mission, and decide what to do next.",
      "Your mission is already surrounded by people, resources, pathways, and possibilities. The next step is seeing how they connect. Call us, or visit anansiatlas.com. Your organization could be next.",
    ],
  },
];

// ElevenLabs voice settings (tuned for an awake, credible business read — not sleepy).
//
// ⚠️ ENGLISH-LOCKED (Scott, 2026-07-30). Every VO in this pipeline is US English.
// eleven_multilingual_v2 occasionally drifted into another language mid-take on long
// reads — it shipped in a vision-film cut and the drift only surfaced on human
// listening, after render and delivery. eleven_turbo_v2_5 + language_code pins the
// language at the API level (multilingual_v2 has no such parameter — with it, every
// regeneration re-rolls the dice). This object feeds EVERY ad's generation, so the
// lock protects all films. Do not switch back to a multilingual model without a
// per-line language audit of the resulting master.
export const VOICE_SETTINGS = {
  model_id: "eleven_turbo_v2_5",
  language_code: "en",
  voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true },
};
