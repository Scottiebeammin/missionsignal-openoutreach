# Atlas Grant Builder

**Turn what Atlas already knows about your organization into grant-ready answers.**

Grant Builder closes the last gap in the Anansi Atlas workflow:

```
Opportunity Intelligence → Readiness → Grant Preparation → Application Draft
```

A nonprofit opens an opportunity in Atlas, chooses **Start Grant Draft**, and gets a
grant-writing workspace already populated with its own approved organizational
information — plus an explicit, actionable list of what is still missing.

## The three questions

Every screen answers one of these:

| Question | Where it is answered |
| --- | --- |
| What does Atlas already know? | Overview → "What Atlas already knows about you"; each section's **Sources used** and **What Atlas knows for this section** |
| What is still missing? | **Missing Information** tab; per-section **Information needed** panel; Grant Coach findings |
| How do we turn that into a stronger application? | Section drafting + Atlas actions; Grant Coach; **Review** |

**V1.1** adds the step before all of that: paste the funder's real application and Atlas
breaks it into their actual questions — see [APPLICATION_IMPORT.md](APPLICATION_IMPORT.md).

## What it is not

It is not an "AI grant writer". The AI is a *writer*, never a *source*. It may improve
wording, structure, and emphasis. It may not add a single fact about the organization
that the organization did not supply. See [AI_RULES.md](AI_RULES.md).

## Navigation

```
Grant Builder
├── Overview              readiness, sections, the full fact set, grant details, status
├── Application           every section with status, length, sources, gaps
│   └── Section           the answer workspace (question, guidance, draft, coach, library)
├── Missing Information   every gap, what it blocks, and where to fix it
├── Answer Library        the organization's reusable approved answers
└── Review                explainable metrics + the issue list before submission
    └── Full draft        copy-all / per-answer copy / print → PDF
```

## Where the code lives

```
openoutreach/grants/
    models.py                GrantApplication, GrantApplicationSection, GrantAnswerLibraryItem
    views.py, urls.py        portal views (names: project-grant-*)
    admin.py
    exceptions.py
    services/
        template.py          the standard 14-section template + information requirements
        context_builder.py   the single organization-data reuse boundary
        applications.py      create/sync workspace, approval, grant readiness
        draft_generator.py   the LLM boundary (anti-fabrication prompt)
        grant_coach.py       rule-based response review + unsupported-claim detection
        answer_library.py    save / suggest / reuse
        completeness.py      the Review screen's metrics and issue list
    templates/grants/*.html
tests/missionsignal/test_grant_builder.py
```

## Related documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — how it fits the existing Atlas architecture
- [DATA_MODEL.md](DATA_MODEL.md) — the three models and why there is no fourth
- [AI_RULES.md](AI_RULES.md) — the factual-integrity guarantee and how it is enforced
- [USER_FLOW.md](USER_FLOW.md) — the client-facing walkthrough
- [APPLICATION_IMPORT.md](APPLICATION_IMPORT.md) — **V1.1**: real application import, the parser, question mapping, and the three-bucket trust model
