# /pipeline-pulse

**Trigger:** `/pipeline-pulse` or "how's the pipeline" or "Monday brief" or "weekly sales review"

**What it does:** Generates a weekly pipeline health report for the Anansi Atlas founding cohort sales process. Flags stale deals, surfaces the top 3 orgs to contact this week, and tracks progress toward the 20-org founding cohort target.

---

## Execution Steps

### Step 1 — Pull Pipeline Data

If HubSpot is connected:
- Pull all active deals and their current stages
- Flag any deal with no activity in 7+ days
- Count deals by stage

If HubSpot is not connected:
- Prompt Marcus to describe his current pipeline (can be a quick verbal rundown)

### Step 2 — Build the Pipeline Snapshot

```
FOUNDING COHORT PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━
Target:    20 orgs
Active:    [N] deals in pipeline
Closed:    [N] active pilots / intakes submitted
Remaining: [N] spots

PIPELINE BY STAGE
─────────────────
Prospect:                [N]
Researched:              [N]
Outreach Sent:           [N]
Replied:                 [N]
Discovery Call Sched:    [N]
Discovery Completed:     [N]
Intake Submitted:        [N]
Snapshot In Progress:    [N]
Snapshot Delivered:      [N]
Active Pilot:            [N]
```

### Step 3 — Flag Risks

```
⚠️  STALE DEALS (no activity 7+ days):
- [Org] — last activity [date] — [recommended action]

🚨  AT-RISK:
- [Org] — [specific risk signal — e.g., "No response after 2 follow-ups", "Intake submitted but Snapshot not delivered", "3 weeks post-walkthrough, no check-in"]
```

### Step 4 — Top 3 Actions This Week

Prioritize based on:
1. Deals closest to closing (intake submitted or discovery call completed)
2. Stale deals with high ICP fit that need a nudge
3. New prospects ready for first outreach

```
THIS WEEK'S TOP 3:

1. [Org name] — [stage] — ACTION: [specific action to take]
2. [Org name] — [stage] — ACTION: [specific action to take]
3. [Org name] — [stage] — ACTION: [specific action to take]
```

### Step 5 — Checkpoint

Present the full pulse to Marcus. Ask:
- Are there any deals missing from this view?
- Should any deal stage be updated?
- Which of the top 3 actions do you want to tackle first?

---

## Output Format

```markdown
## Pipeline Pulse — Week of [Date]

### Cohort Progress
[Progress snapshot from Step 2]

### Risks
[Flags from Step 3]

### Top 3 This Week
[Actions from Step 4]

---

Ready to run `/prospect-brief [org]` on any of these, or prep a `/client-walkthrough` for any pending calls?
```
