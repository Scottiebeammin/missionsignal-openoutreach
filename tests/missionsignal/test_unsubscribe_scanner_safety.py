"""The unsubscribe link cannot be tripped by a machine, and still works for a person.

Production, 2026-08-19: three consecutive cold sends each recorded an opt-out
19-31 seconds after delivery, from three unrelated organizations on three
different days. The in-house test lead — same send path, same footer, mailbox
behind no gateway — recorded nothing. The cause was that a bare GET on
/unsubscribe/<token>/ wrote the row, and corporate mail security fetches every
URL in an inbound message to scan it. Every real prospect was suppressed about
twenty seconds after arrival without a human ever seeing the mail.

So the contract these tests pin is: a GET changes nothing, an RFC 8058 one-click
POST opts out, our own confirmation button opts out, and the headers that make
the client-native one-click possible are actually on the wire.

Behavior tests, not implementation tests.
"""
from __future__ import annotations

import pytest
from django.core import mail
from django.urls import reverse

from openoutreach.signals.models import EmailOptOut, SalesLead
from openoutreach.signals.unsubscribe import (
    CONFIRM_FIELD,
    ONE_CLICK_FIELD,
    ONE_CLICK_VALUE,
    is_opted_out,
    make_unsubscribe_token,
)

pytestmark = pytest.mark.django_db

RECIPIENT = "info@example-nonprofit.org"


def _url(email: str = RECIPIENT) -> str:
    return reverse("email-unsubscribe", args=[make_unsubscribe_token(email)])


def _lead(email: str = RECIPIENT) -> SalesLead:
    return SalesLead.objects.create(organization="Example Nonprofit", email=email)


# ── 1-3. the scanner case: GET is read-only ─────────────────────────────────

def test_get_does_not_record_an_opt_out(client):
    """The regression itself: a link-scanner fetch must not unsubscribe anyone."""
    response = client.get(_url())
    assert response.status_code == 200
    assert not is_opted_out(RECIPIENT)
    assert EmailOptOut.objects.count() == 0


def test_get_offers_a_button_to_confirm(client):
    body = client.get(_url()).content.decode()
    assert "<form method=\"post\"" in body
    assert CONFIRM_FIELD in body
    assert RECIPIENT in body


def test_a_post_without_the_one_click_body_does_not_opt_out(client):
    """A scanner that probes with POST still carries none of our fields.

    Checked as an exact field/value pair rather than "is this a POST" precisely
    so this case stays safe.
    """
    response = client.post(_url(), {"foo": "bar"})
    assert response.status_code == 200
    assert not is_opted_out(RECIPIENT)


# ── 4-6. the human cases: opting out actually works ─────────────────────────

def test_rfc8058_one_click_post_opts_out(client):
    """What Gmail's and Apple Mail's native Unsubscribe button sends."""
    response = client.post(_url(), {ONE_CLICK_FIELD: ONE_CLICK_VALUE})
    assert response.status_code == 200
    assert is_opted_out(RECIPIENT)
    assert EmailOptOut.objects.get(email=RECIPIENT).source == "one-click"


def test_confirmation_button_opts_out(client):
    response = client.post(_url(), {CONFIRM_FIELD: "1"})
    assert response.status_code == 200
    assert is_opted_out(RECIPIENT)
    assert EmailOptOut.objects.get(email=RECIPIENT).source == "link"


def test_opting_out_twice_is_idempotent(client):
    client.post(_url(), {CONFIRM_FIELD: "1"})
    client.post(_url(), {ONE_CLICK_FIELD: ONE_CLICK_VALUE})
    assert EmailOptOut.objects.filter(email=RECIPIENT).count() == 1


def test_a_get_after_opting_out_says_so_rather_than_asking_again(client):
    client.post(_url(), {CONFIRM_FIELD: "1"})
    body = client.get(_url()).content.decode()
    assert "You're unsubscribed" in body
    assert CONFIRM_FIELD not in body


# ── 7-8. the token still governs ────────────────────────────────────────────

def test_a_tampered_token_opts_nobody_out(client):
    response = client.post(reverse("email-unsubscribe", args=["not-a-real-token"]),
                           {ONE_CLICK_FIELD: ONE_CLICK_VALUE})
    assert response.status_code == 400
    assert EmailOptOut.objects.count() == 0


def test_the_token_decides_whose_address_is_suppressed(client):
    """The signed token is the authorisation, which is why the view is CSRF-exempt."""
    client.post(_url("someone@other-org.org"), {ONE_CLICK_FIELD: ONE_CLICK_VALUE})
    assert is_opted_out("someone@other-org.org")
    assert not is_opted_out(RECIPIENT)


# ── 9-11. the headers that make client-native one-click possible ────────────

def test_outbound_mail_carries_the_rfc8058_headers():
    from openoutreach.signals.outreach import send_outreach_email

    lead = _lead()
    send_outreach_email(lead, "hi", "body")
    sent = mail.outbox[0]
    assert sent.extra_headers["List-Unsubscribe-Post"] == f"{ONE_CLICK_FIELD}={ONE_CLICK_VALUE}"
    assert "List-Unsubscribe" in sent.extra_headers


def test_the_list_unsubscribe_header_offers_https_first_then_mailto():
    """RFC 8058 requires an HTTPS URI; clients take the first usable option."""
    from openoutreach.signals.outreach import send_outreach_email

    lead = _lead()
    send_outreach_email(lead, "hi", "body")
    header = mail.outbox[0].extra_headers["List-Unsubscribe"]
    assert header.startswith("<https://")
    assert "<mailto:" in header
    assert header.index("https://") < header.index("mailto:")


def test_the_header_url_is_the_one_that_opts_this_recipient_out(client):
    """The header is not decorative — the URL in it has to actually work."""
    from openoutreach.signals.outreach import send_outreach_email

    lead = _lead()
    send_outreach_email(lead, "hi", "body")
    header = mail.outbox[0].extra_headers["List-Unsubscribe"]
    https_uri = header.split(">")[0].lstrip("<")
    path = "/" + https_uri.split("/", 3)[3]

    assert not is_opted_out(RECIPIENT)
    client.post(path, {ONE_CLICK_FIELD: ONE_CLICK_VALUE})
    assert is_opted_out(RECIPIENT)


def test_adding_the_headers_did_not_displace_the_message_id():
    """Reply correlation depends on this exact header surviving.

    Pinned against the persisted row rather than a literal domain: the ID is
    anchored to the From address, which differs per environment, and what
    correlation actually needs is that the wire header and the stored value are
    the same string.
    """
    from openoutreach.signals.outreach import send_outreach_email
    from openoutreach.signals.models import OutreachMessage

    lead = _lead()
    send_outreach_email(lead, "hi", "body")
    stored = OutreachMessage.objects.get(lead=lead, status=OutreachMessage.Status.SENT)
    assert stored.message_id
    assert mail.outbox[0].extra_headers["Message-ID"] == stored.message_id
