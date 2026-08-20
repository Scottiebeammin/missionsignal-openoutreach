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
* **GET never records. POST records.** This reverses the original design, and
  the reason is worth keeping. Recording on GET was chosen so that a recipient
  who clicks once and closes the tab is still honoured — sound reasoning, but it
  assumed the only thing following the link would be a person. It isn't.
  Corporate mail security (Defender Safe Links, Proofpoint URL Defense,
  Mimecast, Barracuda) fetches every URL in an inbound message to scan it, and
  that fetch is indistinguishable from a click.

  Measured on production, 2026-08-19: three consecutive cold sends each recorded
  an opt-out **19–31 seconds after delivery** (#242 +31.0s, #243 +18.8s,
  #245 +20.2s) — three unrelated organizations, three different days. The
  in-house test lead, same send path and same footer but a mailbox behind no
  gateway, recorded nothing. Every real prospect the warmup touched was
  permanently suppressed about twenty seconds after arrival, and no human ever
  saw the mail. A GET that mutates state was the whole bug.
* **Genuine one-click survives, via RFC 8058.** ``List-Unsubscribe`` plus
  ``List-Unsubscribe-Post: List-Unsubscribe=One-Click`` makes the recipient's
  own mail client (Gmail's and Apple Mail's native Unsubscribe button) send a
  POST carrying exactly ``List-Unsubscribe=One-Click``. Scanners issue GET and
  never that payload, so the one-click path stays one click for the people it
  was built for while being invisible to the machines. Gmail and Yahoo both
  expect these headers on bulk mail regardless, so this also helps deliverability.
* **The body link costs one extra click.** Following it renders a confirmation
  page with a button; the button POSTs. That is the CAN-SPAM-compliant floor —
  a working opt-out mechanism — and it is the only path a scanner can reach.
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

#: The exact form body RFC 8058 requires a one-click unsubscribe POST to carry.
#: Checked as an exact pair rather than "is this a POST" so that a scanner which
#: probes with POST (rare, but they exist) still cannot record an opt-out.
ONE_CLICK_FIELD = "List-Unsubscribe"
ONE_CLICK_VALUE = "One-Click"

#: The field our own confirmation page posts. Distinct from the RFC 8058 pair so
#: the two paths stay separately attributable in ``EmailOptOut.source``.
CONFIRM_FIELD = "confirm_unsubscribe"


def make_unsubscribe_token(email: str) -> str:
    return signing.dumps({"email": (email or "").strip().lower()}, salt=UNSUB_SALT)


def read_unsubscribe_token(token: str) -> str | None:
    """Return the email address, or None if the token is invalid. Never expires."""
    try:
        data = signing.loads(token, salt=UNSUB_SALT)
    except signing.BadSignature:
        return None
    return (data or {}).get("email") or None


def _base_url(base_url: str = "") -> str:
    from django.conf import settings

    return (base_url or getattr(settings, "SITE_BASE_URL", "") or "https://anansiatlas.com").rstrip("/")


def unsubscribe_url(email: str, base_url: str = "") -> str:
    return f"{_base_url(base_url)}/unsubscribe/{make_unsubscribe_token(email)}/"


def list_unsubscribe_headers(email: str, base_url: str = "") -> dict[str, str]:
    """RFC 2369 + RFC 8058 headers for one outbound message.

    Two mechanisms are offered. The HTTPS URI is what a client uses for the
    native one-click button (RFC 8058 requires an HTTPS URI to be present, and
    it is listed first because clients prefer the first usable option); the
    mailto is the fallback for clients that do not implement one-click, and it
    lands in marcus@ to be honoured by hand.

    ``List-Unsubscribe-Post`` is only meaningful alongside ``List-Unsubscribe``,
    and asserts that the URI accepts an unauthenticated POST — which the view
    does, deliberately CSRF-exempt, because the POST originates from the
    recipient's mail provider and carries no session.
    """
    if not email:
        return {}
    https_uri = unsubscribe_url(email, base_url)
    mailto = "mailto:marcus@anansiatlas.com?subject=unsubscribe"
    return {
        "List-Unsubscribe": f"<{https_uri}>, <{mailto}>",
        "List-Unsubscribe-Post": f"{ONE_CLICK_FIELD}={ONE_CLICK_VALUE}",
    }


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


def _is_one_click_post(request) -> bool:
    """True for an RFC 8058 one-click POST from the recipient's mail provider."""
    return request.method == "POST" and request.POST.get(ONE_CLICK_FIELD) == ONE_CLICK_VALUE


def _is_confirmed_post(request) -> bool:
    """True for a POST from our own confirmation page's button."""
    return request.method == "POST" and bool(request.POST.get(CONFIRM_FIELD))


_PAGE = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{title} · Anansi Atlas</title>
<style>
 body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
      background:#0D1B3D;color:#fff;display:flex;min-height:100vh;align-items:center;
      justify-content:center;margin:0;padding:24px;line-height:1.55}}
 .card{{max-width:34rem}} h1{{font-size:1.5rem;margin:0 0 .75rem}}
 p{{color:#cdd5e8;margin:.6rem 0}} .mark{{color:#D4A017;font-weight:600;letter-spacing:.02em}}
 a{{color:#D4A017}}
 button{{background:#D4A017;color:#0D1B3D;border:0;border-radius:6px;font-size:1rem;
        font-weight:600;padding:.7rem 1.4rem;margin-top:.9rem;cursor:pointer;
        font-family:inherit}}
 button:hover{{background:#e0af2b}}
</style>
<div class="card">
  <p class="mark">ANANSI ATLAS</p>
  <h1>{title}</h1>
  {body}
</div>"""

_BAD_TOKEN_BODY = (
    "<p>We couldn't read that unsubscribe link — it may have been "
    "cut short by an email client.</p><p>Reply to the message with the word "
    "<strong>unsubscribe</strong> and we'll take you off the list by hand, "
    "or write to <a href='mailto:marcus@anansiatlas.com'>marcus@anansiatlas.com</a>.</p>"
)


def _done_page(email: str) -> HttpResponse:
    return HttpResponse(_PAGE.format(
        title="You're unsubscribed",
        body=f"<p><strong>{email}</strong> won't receive any further outreach from Anansi Atlas.</p>"
             "<p>No further action needed, and sorry for the interruption.</p>",
    ))


@csrf_exempt
def unsubscribe(request, token):
    """Honour an opt-out on POST. Idempotent — a second visit says the same thing.

    CSRF-exempt because both POST paths are legitimately session-less: the RFC
    8058 one-click POST comes from the recipient's mail provider, and the
    confirmation page is served to a recipient who has no account here. The
    signed token is the authorisation — it proves the requester holds a link we
    minted for that specific address, which is exactly the property CSRF
    protection would otherwise supply.
    """
    email = read_unsubscribe_token(token)
    if not email:
        return HttpResponse(
            _PAGE.format(title="That link didn't work", body=_BAD_TOKEN_BODY),
            status=400,
        )

    if _is_one_click_post(request):
        record_opt_out(email, source="one-click")
        return _done_page(email)

    if _is_confirmed_post(request):
        record_opt_out(email, source="link")
        return _done_page(email)

    # Anything else — including every GET, and so including every automated
    # link-scanner fetch — is read-only. Nothing is recorded here.
    if is_opted_out(email):
        return _done_page(email)

    return HttpResponse(_PAGE.format(
        title="Unsubscribe?",
        body=f"<p>Confirm and <strong>{email}</strong> won't receive any further "
             "outreach from Anansi Atlas.</p>"
             f'<form method="post" action="{request.path}">'
             f'<button type="submit" name="{CONFIRM_FIELD}" value="1">Unsubscribe me</button>'
             "</form>",
    ))
