"""Gmail read-only transport for inbound ingestion.

Why Gmail API over IMAP or forwarding
-------------------------------------
The tenant is Google Workspace; the app is a Render web service with no
long-lived worker; the established job mechanism is Render cron running a
management command. Within that:

* **Gmail API** gives scoped read-only OAuth (``gmail.readonly``), full header
  access, a real incremental cursor (``history.list``), and no risk of the
  mark-as-read side effects IMAP clients can inflict. Polling from a cron
  command fits it exactly.
* **IMAP** would need per-mailbox app passwords (a broader credential than a
  read-only scope), Workspace IMAP enablement, and hand-rolled incremental
  state (UIDVALIDITY bookkeeping); its failure modes include accidental flag
  mutation. Strictly worse here.
* **Forwarding/webhook** ingestion needs Workspace routing changes plus a
  public endpoint parsing raw MIME from the open internet — more admin surface
  and more attack surface, for no gain at this volume.

Auth architecture (no secrets in the repo)
------------------------------------------
A **service account with domain-wide delegation**, impersonating each
configured mailbox, scope ``https://www.googleapis.com/auth/gmail.readonly``
and nothing else. Required setup (one-time, by Marcus / the Workspace admin —
none of it can be done from this repo):

1. Google Cloud console → create (or reuse) a project → enable the Gmail API.
2. Create a service account; create a JSON key for it.
3. On the service account, enable domain-wide delegation; note its Client ID.
4. Workspace Admin console → Security → API Controls → Domain-wide Delegation →
   add that Client ID with exactly the scope
   ``https://www.googleapis.com/auth/gmail.readonly``.
5. Render → Environment:
   - ``GOOGLE_SERVICE_ACCOUNT_JSON`` — the key file's contents (the whole JSON,
     as a single env value);
   - ``OUTREACH_REPLY_MAILBOX``  (e.g. ``marcus@anansiatlas.com``);
   - ``OUTREACH_BOUNCE_MAILBOX`` (e.g. ``mail@anansiatlas.com``).

The two mailbox settings are deliberately explicit configuration, not
hard-coded: if ``mail@`` turns out to be an alias of ``marcus@`` rather than a
mailbox, point both settings at the one real mailbox — ingestion deduplicates
on (mailbox, gmail_id), so nothing else changes.

Read-only by construction
-------------------------
This transport exposes exactly two operations: list new message ids and fetch a
message's metadata/body. There is no method that could modify, label, archive,
mark read, delete, or send — the capability is absent from the interface, not
merely unused, and the OAuth scope would refuse it anyway.

Import discipline: the google client libraries are imported lazily inside
``GmailTransport`` so the web app never needs them; only the ingestion cron
does, and it fails with a clear message if they are missing or unconfigured.
"""
from __future__ import annotations

import base64
import logging
import os
import re
from email.utils import parsedate_to_datetime

from openoutreach.signals.ingest import FetchedMessage

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

#: First-ever run (no cursor) and cursor-expired recovery both sweep a bounded
#: recent window rather than the whole mailbox. Idempotency makes the overlap free.
BASELINE_QUERY = "newer_than:14d"
RECOVERY_QUERY = "newer_than:30d"

_WANTED_HEADERS = [
    "Message-ID", "In-Reply-To", "References", "From", "To", "Subject", "Date",
    "Auto-Submitted", "X-Autoreply", "X-Autorespond", "X-Failed-Recipients",
    "Content-Type",
]


def reply_mailbox() -> str:
    return os.getenv("OUTREACH_REPLY_MAILBOX", "").strip().lower()


def bounce_mailbox() -> str:
    return os.getenv("OUTREACH_BOUNCE_MAILBOX", "").strip().lower()


def configured_mailboxes() -> list[str]:
    """The distinct mailboxes to poll — one entry when both settings point at
    the same box (the alias case), two when they differ."""
    boxes = [b for b in (reply_mailbox(), bounce_mailbox()) if b]
    seen: list[str] = []
    for b in boxes:
        if b not in seen:
            seen.append(b)
    return seen


class GmailNotConfigured(RuntimeError):
    pass


class GmailTransport:
    """Fetch-only Gmail access for one impersonated mailbox."""

    def __init__(self, mailbox: str):
        self.mailbox = mailbox
        self._service = self._build_service(mailbox)

    @staticmethod
    def _build_service(mailbox: str):
        raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if not raw:
            raise GmailNotConfigured(
                "GOOGLE_SERVICE_ACCOUNT_JSON is not set — see gmail_transport.py for the "
                "one-time Google Cloud / Workspace setup.")
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover — environment, not logic
            raise GmailNotConfigured(
                "google-api-python-client / google-auth are not installed in this "
                "environment (they are in requirements/web.txt)."
            ) from exc
        import json

        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES, subject=mailbox)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    # ── the two (and only two) operations ────────────────────────────────────

    def fetch_new(self, history_id: str) -> tuple[list[FetchedMessage], str]:
        """(new messages, next cursor). Never mutates anything in the mailbox.

        With a cursor: ``history.list(startHistoryId=…)``, collecting
        ``messagesAdded``. A 404 means Gmail expired the cursor — recovery is a
        bounded re-sweep (RECOVERY_QUERY) plus a fresh cursor; idempotent
        ingestion absorbs the overlap. Without a cursor: a bounded baseline
        sweep (BASELINE_QUERY).
        """
        from googleapiclient.errors import HttpError

        users = self._service.users()
        if history_id:
            try:
                ids, new_cursor = self._ids_from_history(users, history_id)
            except HttpError as exc:
                if getattr(exc, "status_code", None) == 404 or "404" in str(exc):
                    logger.warning("gmail: history cursor expired for %s — bounded recovery sweep",
                                   self.mailbox)
                    ids, new_cursor = self._ids_from_query(users, RECOVERY_QUERY)
                else:
                    raise
        else:
            ids, new_cursor = self._ids_from_query(users, BASELINE_QUERY)
        return [self._fetch_one(users, gmail_id) for gmail_id in ids], new_cursor

    # ── internals ────────────────────────────────────────────────────────────

    def _ids_from_history(self, users, history_id: str) -> tuple[list[str], str]:
        ids: list[str] = []
        latest = history_id
        page_token = None
        while True:
            resp = users.history().list(
                userId="me", startHistoryId=history_id,
                historyTypes=["messageAdded"], pageToken=page_token).execute()
            latest = str(resp.get("historyId", latest))
            for entry in resp.get("history", []):
                for added in entry.get("messagesAdded", []):
                    ids.append(added["message"]["id"])
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return ids, latest

    def _ids_from_query(self, users, query: str) -> tuple[list[str], str]:
        ids: list[str] = []
        page_token = None
        while True:
            resp = users.messages().list(userId="me", q=query,
                                         pageToken=page_token, maxResults=100).execute()
            ids.extend(m["id"] for m in resp.get("messages", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        profile = users.getProfile(userId="me").execute()
        return ids, str(profile.get("historyId", ""))

    def _fetch_one(self, users, gmail_id: str) -> FetchedMessage:
        raw = users.messages().get(
            userId="me", id=gmail_id, format="full",
            metadataHeaders=_WANTED_HEADERS).execute()
        payload = raw.get("payload", {}) or {}
        headers = {h["name"]: h["value"]
                   for h in payload.get("headers", []) if h.get("name") in _WANTED_HEADERS}
        date = None
        if headers.get("Date"):
            try:
                date = parsedate_to_datetime(headers["Date"])
            except (TypeError, ValueError):
                date = None
        return FetchedMessage(
            gmail_id=gmail_id,
            thread_id=raw.get("threadId", ""),
            rfc_message_id=headers.get("Message-ID", ""),
            in_reply_to=headers.get("In-Reply-To", ""),
            references=headers.get("References", ""),
            from_address=headers.get("From", ""),
            to_addresses=headers.get("To", ""),
            subject=headers.get("Subject", ""),
            date=date,
            body_text=_extract_text(payload) or raw.get("snippet", ""),
            headers=headers,
        )


def _extract_text(payload: dict) -> str:
    """Best-effort text/plain body out of a Gmail payload tree; HTML stripped crudely."""
    def walk(part) -> str:
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if mime == "text/plain" and data:
            return _b64(data)
        for child in part.get("parts", []) or []:
            found = walk(child)
            if found:
                return found
        if mime == "text/html" and data:
            return re.sub(r"<[^>]+>", " ", _b64(data))
        return ""

    return walk(payload).strip()


def _b64(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — malformed part, not a pipeline failure
        return ""
