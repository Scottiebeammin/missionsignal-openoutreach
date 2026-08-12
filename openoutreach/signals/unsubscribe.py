"""One-click opt-out for outbound cold email.

CAN-SPAM requires every commercial message to carry a working opt-out and a
valid physical postal address, and requires opt-outs to be honoured. Before this
existed, outreach mail had neither.

Design notes:

* **The link is a signed token, not an email address in a query string.** A URL
  like ``/unsubscribe/?email=someone@org.org`` lets anyone unsubscribe anyone,
  and leaks an address into logs, referrers and analytics. ``signing.dumps``
  gives a tamper-evident token instead, same mechanism the project already uses
  for project invites.
* **No expiry.** Invite tokens expire after 14 days; an opt-out link must work
  whenever the recipient gets round to it — including on a mail they find a year
  later. A link that has expired is not a working opt-out.
* **GET records the opt-out.** Requiring a confirmation click means a recipient
  who clicks once and closes the tab is still on the list, which is not what
  they asked for. Honour it immediately and say so on the page.
* **Suppression is enforced in the send path, not in the caller.** Anything that
  sends has to go through ``send_outreach_email``, so the check belongs there —
  a rule that depends on every future caller remembering it isn't a rule.
"""
from __future__ import annotations

from django.core import signing
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

UNSUB_SALT = "anansi-email-optout"


def make_unsubscribe_token(email: str) -> str:
    return signing.dumps({"email": (email or "").strip().lower()}, salt=UNSUB_SALT)


def read_unsubscribe_token(token: str) -> str | None:
    """Return the email address, or None if the token is invalid. Never expires."""
    try:
        data = signing.loads(token, salt=UNSUB_SALT)
    except signing.BadSignature:
        return None
    return (data or {}).get("email") or None


def unsubscribe_url(email: str, base_url: str = "") -> str:
    from django.conf import settings

    base = (base_url or getattr(settings, "SITE_BASE_URL", "") or "https://anansiatlas.com").rstrip("/")
    return f"{base}/unsubscribe/{make_unsubscribe_token(email)}/"


def is_opted_out(email: str) -> bool:
    from openoutreach.signals.models import EmailOptOut

    if not email:
        return False
    return EmailOptOut.objects.filter(email=email.strip().lower()).exists()


def record_opt_out(email: str, source: str = "link") -> None:
    from openoutreach.signals.models import EmailOptOut

    if not email:
        return
    EmailOptOut.objects.get_or_create(
        email=email.strip().lower(),
        defaults={"source": source, "created_at": timezone.now()},
    )


_PAGE = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Anansi Atlas</title>
<style>
 body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
      background:#0D1B3D;color:#fff;display:flex;min-height:100vh;align-items:center;
      justify-content:center;margin:0;padding:24px;line-height:1.55}}
 .card{{max-width:34rem}} h1{{font-size:1.5rem;margin:0 0 .75rem}}
 p{{color:#cdd5e8;margin:.6rem 0}} .mark{{color:#D4A017;font-weight:600;letter-spacing:.02em}}
 a{{color:#D4A017}}
</style>
<div class="card">
  <p class="mark">ANANSI ATLAS</p>
  <h1>{title}</h1>
  {body}
</div>"""


@csrf_exempt
def unsubscribe(request, token):
    """Honour an opt-out immediately. Idempotent — a second visit says the same thing."""
    email = read_unsubscribe_token(token)
    if not email:
        return HttpResponse(
            _PAGE.format(
                title="That link didn't work",
                body="<p>We couldn't read that unsubscribe link — it may have been "
                     "cut short by an email client.</p><p>Reply to the message with the word "
                     "<strong>unsubscribe</strong> and we'll take you off the list by hand, "
                     "or write to <a href='mailto:marcus@anansiatlas.com'>marcus@anansiatlas.com</a>.</p>",
            ),
            status=400,
        )
    record_opt_out(email, source="link")
    return HttpResponse(_PAGE.format(
        title="You're unsubscribed",
        body=f"<p><strong>{email}</strong> won't receive any further outreach from Anansi Atlas.</p>"
             "<p>No further action needed, and sorry for the interruption.</p>",
    ))
