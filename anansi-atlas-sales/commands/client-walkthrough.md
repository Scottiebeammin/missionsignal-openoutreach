# /client-walkthrough

**Trigger:** `/client-walkthrough [org name or project ID]`

**What it does:** Prepares a complete session package for a founder walkthrough — the 45-minute call where you walks a client through their Opportunity Web Snapshot for the first time. Generates a pre-read brief, session agenda, talk tracks, and follow-up template.

---

## Execution Steps

### Step 1 — Pull Client Data

If HubSpot is connected:
- Pull the contact record and deal stage
- Pull any logged call notes or prior interactions

From the Anansi Atlas database (via context or provided manually):
- Organization name, focus areas, beneficiaries
- `intake_notes` — read these first, they are the most important signal
- Budget range and current funding sources
- Existing partnerships
- Top opportunity matches from their Snapshot

If data is not available via MCP, prompt you to paste or describe:
- The org's intake notes
- Their top 3 Snapshot matches
- Any prior conversations or email threads

### Step 2 — Build the Pre-Read Brief

A 1-page summary you reviews before the call:

```
CLIENT: [Org name]
CONTACT: [Name, Title]
CALL DATE/TIME: [if known]

THEIR STATED CHALLENGE (from intake notes):
"[Direct quote from intake_notes]"

SNAPSHOT HIGHLIGHTS:
- Top funder match: [Name + why aligned]
- Top partnership match: [Name + why aligned]
- Most important readiness gap: [Gap + what closing it looks like]
- Strongest government pathway: [if any]

WHAT TO LEAD WITH:
[Single most compelling insight from their Snapshot — the thing they almost certainly don't know]

WHAT TO WATCH FOR:
[Signal from their intake or org type that suggests specific concern or opportunity]

CALL GOAL:
[Concrete outcome — e.g., "Get them to commit to pursuing [Funder X] and schedule a check-in in 2 weeks"]
```

### Step 3 — Generate Session Agenda

```
WALKTHROUGH AGENDA — [Org Name] — [Date]

0:00–0:05  Opening
  - "Before we dive in, you mentioned [quote from intake_notes] — I want to make sure we spend real time on that."
  - Quick recap of what the Snapshot covers

0:05–0:10  Opportunity Web Overview
  - Show the web visualization
  - Frame: "Every node is a real, active opportunity that's aligned to your specific mission."

0:10–0:20  Funder Matches
  - Walk through top 3 funders with you's commentary
  - For each: "Here's why this one is aligned to your work specifically."
  - Identify which one they should pursue first

0:20–0:28  Partnership + Government Pathways
  - Top 2 partnership matches — who they are and why they matter
  - Any government pathway (CDBG, DOL, HUD, etc.) that fits their work
  - "Partnership conversations can strengthen your grant applications before you write a word."

0:28–0:36  Readiness Gaps (don't skip this section)
  - Name the gaps honestly
  - For each gap: "Here's what closing this looks like. It's not a blocker — it's a roadmap."
  - Frame gaps as the most valuable part of the Snapshot

0:36–0:42  30-Day Action Plan
  - Walk through their specific action items
  - Make it concrete: "Your first move is X, this week, because Y."
  - Ask: "Which of these feels most urgent to you?"

0:42–0:45  Close
  - Confirm their top 1-2 actions
  - Ask: "Is there a specific funder or partner you want to dig into more before we reconnect?"
  - Schedule follow-up (2 weeks is standard)
  - "I'll send you a summary of today's conversation within 24 hours."
```

### Step 4 — Draft Post-Call Follow-Up Email

Generate after the call (or in advance as a template):

```
Subject: Your Anansi Atlas Walkthrough — Key Takeaways + Next Steps

[First name],

Thank you for the time today. A few things I want to make sure stay top of mind:

YOUR TOP OPPORTUNITY RIGHT NOW:
[Funder or pathway name] — [1-2 sentence explanation of why it's the right move and what action they should take]

THE READINESS GAP TO CLOSE FIRST:
[Gap name] — [1 sentence on what closing it looks like in practice]

YOUR 30-DAY ACTIONS:
1. [Specific action 1]
2. [Specific action 2]
3. [Specific action 3]

I'll check in [date — 2 weeks from call] to see how [Action 1] is going. In the meantime, your full Snapshot is at [link to their workspace].

If anything comes up before then, reply here or book time directly: [Calendly link]

— you
```

### Step 5 — Checkpoint

Present the pre-read brief, session agenda, and follow-up draft to you. Ask:
1. Does the pre-read capture what you know about this client?
2. Is the "what to lead with" the right hook, or do you want to adjust based on a prior conversation?
3. Should the 30-day actions be adjusted?
4. Ready to log this to HubSpot?

---

## Output Format

```markdown
## Walkthrough Package — [Org Name]

### Pre-Read Brief
[Brief from Step 2]

---

### Session Agenda
[Agenda from Step 3]

---

### Post-Call Follow-Up (template)
[Email from Step 4]

---

### Next Step
[ ] Review and adjust before the call
[ ] Log prep to HubSpot
[ ] Send follow-up after the call
```
