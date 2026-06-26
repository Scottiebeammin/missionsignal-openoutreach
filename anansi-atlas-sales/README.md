# Anansi Atlas Sales Plugin — Hermes

**Hermes** is the AI sales and client intelligence layer for Anansi Atlas. It handles nonprofit prospect research, personalized outreach drafting, founder walkthrough preparation, and pipeline management for the founding cohort.

## Commands

| Command | What It Does |
|---------|-------------|
| `/prospect-brief [org name or URL]` | Full prospect research + personalized cold email + LinkedIn DM, ready to review and send |
| `/client-walkthrough [org name]` | Pre-read brief + session agenda + follow-up template for a founder walkthrough |
| `/pipeline-pulse` | Weekly pipeline health — cohort progress, stale deals, top 3 actions this week |

## Skills (Auto-Triggered)

| Skill | Activates When... |
|-------|-----------------|
| `nonprofit-outreach` | You ask about researching a nonprofit, drafting outreach, handling objections, or discussing value props |
| `client-intelligence` | You ask about preparing for a call, understanding a client's Snapshot, or debriefing after a session |

## Setup

1. Copy `settings.local.json` and fill in your Calendly link and email
2. Connect MCP tools in `.mcp.json` (HubSpot required for CRM logging; Gmail for email staging)
3. Install in Claude Code: `claude plugin install ./anansi-atlas-sales`

## MCP Connectors

| Tool | Required For |
|------|-------------|
| HubSpot | Pipeline tracking, deal logging, contact management |
| Gmail | Staging outreach drafts for review before send |
| Slack | Optional — weekly pipeline brief delivery |
| Klaviyo | Optional — automated nurture sequences for post-signup orgs |

## Philosophy

Hermes does research and drafting. Marcus reviews and approves before anything goes out. Every command pauses for a checkpoint before taking action in external tools (CRM, email). The intelligence is automated; the relationships stay human.
