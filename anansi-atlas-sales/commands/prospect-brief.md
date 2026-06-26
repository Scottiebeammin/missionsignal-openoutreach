# /prospect-brief

**Trigger:** `/prospect-brief [org name or website]`

**What it does:** End-to-end prospect research + personalized outreach in one command. Takes a nonprofit name or website, builds a full intelligence brief, maps them to Anansi Atlas value props, and drafts a personalized cold email and LinkedIn DM — ready for Marcus to review and send.

---

## Execution Steps

### Step 1 — Identify the Org
- If given a name, search for their website, LinkedIn page, and ProPublica 990 record
- If given a URL, scrape the homepage and pull mission, programs, geography, and staff signals
- Confirm this is a real nonprofit (not a for-profit with nonprofit language)

### Step 2 — Build the Intelligence Brief

Output a structured brief with:

```
ORG: [Name]
WEBSITE: [URL]
LOCATION: [City, State]
NTEE CODE: [if findable]
EST. BUDGET: [from 990 or estimate from signals]
FOCUS AREA(S): [primary mission categories]
BENEFICIARIES: [who they serve]
STAGE: [early / growth / established]

REVENUE PICTURE (from 990 or signals):
- Government: [%]
- Foundation: [%]
- Individual: [%]
- Earned: [%]
- Risk flag: [if >70% from single source, flag it]

KEY PEOPLE:
- [Name, Title] — [LinkedIn URL if found]

TRIGGER SIGNALS:
- [List any of: new program, hiring signal, recent grant, new ED, capital campaign, etc.]

FUNDER LANDSCAPE (sector-specific):
- [2-3 active funders in their focus area they may not be pursuing]

PARTNERSHIP ANGLE:
- [1-2 org types or specific orgs that would strengthen their work]

ICP FIT: [High / Medium / Low]
REASON: [1 sentence on why they're a strong/weak fit for Anansi Atlas right now]
```

### Step 3 — Map to Anansi Atlas Value Props

Based on their focus area and revenue picture, select the most resonant value prop from `nonprofit-outreach.md`.

Identify the **single most compelling hook** for this specific org — the thing Anansi Atlas shows them that they almost certainly don't know yet.

### Step 4 — Draft the Cold Email

Use the GLF framework from `nonprofit-outreach.md`. Output:

```
SUBJECT: [specific, curiosity-driven, under 8 words — never starts with "Quick question" or "Following up"]

BODY:
[Hook — specific observation about their org, 1-2 lines]

[The shift — name the problem Anansi Atlas solves for orgs like theirs, 1-2 lines]

[The offer — what their Snapshot would surface for them specifically, 1 line]

[CTA — single link, single action]

— Marcus Scott
Founder, Anansi Atlas
[calendly link from settings if available]
```

Target: under 140 words. No filler lines.

### Step 5 — Draft the LinkedIn DM

Shorter version for LinkedIn connection message or DM:
- Under 75 words
- Reference one specific thing from their profile or org
- Single CTA

### Step 6 — Checkpoint Before Sending

**Pause here.** Present the brief, email, and DM to Marcus. Ask:
1. Does the intelligence brief look accurate?
2. Should the email hook change based on anything you know about this org?
3. Do you want to adjust the CTA (Calendly link vs. direct intake link)?
4. Ready to stage this in Gmail / log to HubSpot?

Only proceed to logging or staging after explicit approval.

### Step 7 — Log to HubSpot (if connected)

If HubSpot MCP is connected and Marcus approves:
- Create contact record for the key person identified
- Create deal record at stage "researched"
- Log the intelligence brief as a note
- Set follow-up task for 4 days out (first follow-up timing per the outreach sequence)

---

## Output Format

```markdown
## Prospect Brief — [Org Name]

### Intelligence
[Full brief from Step 2]

### Why Anansi Atlas
[Value prop mapping from Step 3]

---

### Cold Email (Gmail-ready)

**Subject:** [subject line]

[email body]

---

### LinkedIn DM

[DM text]

---

### Next Step
[ ] Approve and stage email in Gmail
[ ] Log to HubSpot
[ ] Adjust before sending
```
