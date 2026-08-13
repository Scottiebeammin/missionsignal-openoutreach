# Outreach Live-Autonomy Canary — Runbook

The first live autonomous send must be deliberately tiny, fully observed, and
reversible at every step. This is the procedure. Do not improvise past it.

**Precondition — do not start until all of these are true:**

1. Google mailbox ingestion is live in production: `MailboxCursor` rows for the
   configured mailbox(es) show a recent `last_success_at` and empty
   `last_error`, populated by the `anansi-ingest-outreach-mail` cron (not by a
   one-off manual run).
2. At least one full day of production **shadow** runs has been reviewed at
   `/operator/runner/` and every `WOULD_SEND_*` decision matched Marcus's own
   judgement. Real disagreements were fixed and re-validated — not overridden.
3. `python manage.py check_research_readiness` reports READY for the campaign
   segment.
4. The cockpit and the Workspace mailbox are both open and watched for the
   duration.

**The canary run:**

1. Pick 1–3 candidates from the latest shadow run's `WOULD_SEND_*` list and
   re-read each draft by hand — this is the last human review before autonomy.
2. In Render → Environment, set **temporarily**:
   - `OUTREACH_AUTOSEND_ENABLED=true`
   - `OUTREACH_DAILY_SEND_LIMIT=<canary size, e.g. 1>`
   (leave `OUTREACH_MAX_SENDS_PER_RUN` at its default of 1.)
3. Run once, by hand, in the Render shell — no cron yet:
   `python manage.py run_outreach_campaign --live`
4. Verify, in order:
   - the command output shows exactly one `LIVE_SENT` and a clean summary;
   - `/operator/runner/` shows the live decision row;
   - the `OutreachMessage` row is SENT with `sent_at` and a domain-anchored
     `message_id`;
   - the email is visible in the Workspace **Sent** folder of `mail@` (the
     From mailbox) and `marcus@` received the CC copy;
   - the recipient's copy carries the unsubscribe footer and mailing address.
5. Send a controlled reply from an outside mailbox to the canary message.
6. Wait for (or manually run) `ingest_outreach_mail`, then verify:
   - the reply appears at `/operator/replies/` with `needs_attention`;
   - it is attributed to the exact canary touch (In-Reply-To correlation);
   - the lead's outcome is REPLIED;
   - a further `run_outreach_campaign --live` classifies the lead
     HOLD_REPLIED and sends nothing.
7. **Immediately after the canary: set `OUTREACH_AUTOSEND_ENABLED=false`** and
   restore `OUTREACH_DAILY_SEND_LIMIT`. Autonomy stays off until the scaled
   rollout is separately and explicitly decided.

**Abort rule:** any step that does not match expectations stops the canary —
set the flag false first, investigate second. An AMBIGUOUS outcome is not a
retry invitation: verify the Sent folder by hand.

**Scaled rollout (later, separate decision):** add the Render cron
(`*/15 * * * *`, `run_outreach_campaign --live`), keep the daily cap at 20,
and review `/operator/runner/` daily for the first week.
