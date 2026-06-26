# Client Intelligence — Anansi Atlas Sales Skill

## When This Skill Activates

Trigger automatically when Marcus asks to:
- Prepare for a discovery call or walkthrough with a nonprofit
- Understand what an org's Snapshot contains before a conversation
- Generate talk tracks or session agendas for a specific client
- Debrief after a client call and identify next steps
- Understand what a client needs to move forward in the pilot
- Prepare a follow-up email after a client interaction

---

## The Client Journey — How Anansi Atlas Works

Understanding the full journey prevents misalignment in conversations:

```
Landing Page
    ↓
Sign Up (create account)
    ↓
Organization Intake (10-minute form — 7 sections)
    ↓  [auto-analysis runs immediately]
Opportunity Web Snapshot (the product)
    ↓
Founder Walkthrough (Marcus leads 45-min session)
    ↓
Active Pilot (client acts on the Snapshot)
    ↓
Renewal / Case Study
```

The intake form captures:
1. Contact info (name, position, email)
2. Organization identity (name, website, city/state)
3. Mission & programs
4. Focus areas (checkboxes — 20 categories)
5. Who they serve (beneficiary population checkboxes)
6. Funding & capacity context (budget range, current sources, existing partnerships)
7. Notes (their own words about where they need help)

The system auto-scrapes their website, runs deterministic analysis, and populates their Snapshot with:
- Aligned funders (foundations, government, corporate)
- Partnership matches
- Readiness gaps
- Opportunity Web visualization
- 30-day recommended actions

---

## Discovery Call Prep Framework

When preparing for a first call with a prospect or new client, gather:

### 1. Org Intelligence
- 990 data from ProPublica (revenue breakdown, program expenses, salary ratios)
- Mission statement and programs from their website
- Recent grants or partnerships mentioned on LinkedIn or their site
- NTEE code and focus area
- Year founded, staff size estimate, geography

### 2. Snapshot Intelligence (if they've already submitted intake)
From the Anansi Atlas database for this org, surface:
- Their self-reported focus areas and beneficiaries
- Their `intake_notes` (their own words about where they need help — read these carefully)
- Their `budget_range` and `existing_partnerships`
- Top 5 opportunity matches from their Snapshot (funders, partners, government)
- Any readiness gaps flagged in their analysis

### 3. Conversation Frame
Build the call around their `intake_notes` — this is the most valuable signal. If they said *"we're struggling to diversify funding beyond our state contract"*, the call should start there, not with a generic product demo.

---

## Walkthrough Session Guide (45 minutes)

The founder walkthrough is Marcus walking a client through their Snapshot. Structure:

**Opening (5 min):** Recap what they submitted. Confirm their primary challenge. Set expectations for the session.

**Snapshot tour (20 min):**
1. Opportunity Web visualization — "This is the web of aligned opportunity around your mission right now."
2. Top funder matches — walk through the top 3-5 with commentary on why they're aligned
3. Partnership matches — highlight 2-3 that could strengthen their grant applications
4. Government pathways — flag any local/state/federal lanes that match their work
5. Readiness gaps — name the gaps honestly; don't skip these, they're the most valuable part
6. 30-day action plan — make it concrete: "Your first move is X, because Y"

**Q&A and dialogue (15 min):** Let them react. Note every follow-up question — these become the basis for the next session.

**Closing (5 min):** Confirm their top 1-2 actions from the Snapshot. Schedule next check-in. Ask: *"Is there a specific funder or partner from the Snapshot you want to dig into before we reconnect?"*

---

## Talk Track by Client Scenario

### Client just submitted intake, first walkthrough
Opening: *"Before we dive in — you mentioned in your intake notes that [quote their exact words]. I want to make sure we spend real time on that today."*

### Client is overwhelmed, doesn't know where to start
Anchor to the 30-day action plan section: *"Let's ignore everything else for a minute. The Snapshot flagged three things you could move on this week with no budget and minimal bandwidth. Here's the first one."*

### Client is excited about funders but needs to win a grant
Reality-check with readiness gaps: *"The funder alignment is real — [Funder X] is a strong match. But the Snapshot also flagged that [Gap Y] would likely block an application right now. Here's what closing that gap looks like."*

### Client is skeptical about the ROI
Use their own intake data: *"You mentioned [budget range] and [current funding sources]. The Snapshot found [N] funders in your focus area with giving histories in your budget range that you're not currently pursuing. Even one conversation converts."*

### Client wants to talk partnerships, not just funders
*"Partners are actually what strengthens funder applications most. The Snapshot identified [X] organizations working in [their focus area] in [their geography] who either complement your programs or share your funders. Starting a partnership conversation there can strengthen your next grant before you write a word."*

---

## Post-Call Debrief Protocol

After any client call, capture:
1. **What they said about their biggest challenge** (exact quote if possible)
2. **What resonated in the Snapshot** (which section, which specific match)
3. **What they pushed back on or were confused by**
4. **Their stated next action** (what they're going to do before you reconnect)
5. **Your next action** (what you committed to send or prepare)
6. **Pipeline update** — which stage should this deal move to in HubSpot

Use these to update the client's HubSpot record and to prep for the next session.

---

## Client Health Signals

Watch for these in client interactions:

**Positive signals:**
- Asking about specific funders by name
- Mentioning they shared the Snapshot with their board
- Asking how to apply for a funder the Snapshot identified
- Requesting a follow-up walkthrough
- Referring another org ("I told my colleague at [Org X] about this")

**Warning signals:**
- Has not opened the Snapshot in 7+ days after delivery
- Responds to follow-up with "we've been busy" without a concrete next step
- Keeps asking generic questions that suggest they haven't read the Snapshot
- Mentions they're "evaluating other options" (ask what — usually it's inertia, not a real competitor)

**Escalation protocol:**
If a client hasn't engaged after 10 days post-delivery → send a "highlight email" that surfaces their single most compelling funder match with a note: *"This funder has a deadline in [X weeks] — wanted to flag it before it passed."*

---

## CRM Notes Format

When logging a call or interaction in HubSpot, use this structure:

```
DATE: [date]
TYPE: [discovery call / walkthrough / check-in / email / inbound]
PARTICIPANTS: [names and titles]

SUMMARY:
[2-3 sentences on what was discussed]

KEY SIGNALS:
- [Positive or warning signal observed]
- [What they said about their biggest pain point]

NEXT ACTIONS:
- Marcus: [what you committed to do]
- Client: [what they said they would do]
- Follow-up date: [specific date]

DEAL STAGE: [current stage → new stage if changed]
```
