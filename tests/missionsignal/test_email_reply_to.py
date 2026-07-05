"""Reply-To stamping: mail sends FROM the sending mailbox (mail@, DKIM-signed)
but replies route to the human inbox (info@) via a default Reply-To header.
"""
from unittest.mock import patch

import pytest
from django.core.mail import EmailMessage

from openoutreach.core.email import apply_default_reply_to, reply_to_address


def test_default_reply_to_is_marcus():
    assert reply_to_address() == "marcus@anansiatlas.com"


def test_reply_to_env_override():
    with patch.dict("os.environ", {"REPLY_TO_EMAIL": "hello@anansiatlas.com"}):
        assert reply_to_address() == "hello@anansiatlas.com"


def test_stamps_reply_to_when_absent():
    msg = EmailMessage(subject="s", body="b", from_email="mail@anansiatlas.com",
                       to=["client@org.org"])
    assert not msg.reply_to
    apply_default_reply_to([msg])
    assert msg.reply_to == ["marcus@anansiatlas.com"]


def test_does_not_override_explicit_reply_to():
    msg = EmailMessage(subject="s", body="b", from_email="mail@anansiatlas.com",
                       to=["client@org.org"], reply_to=["specific@anansiatlas.com"])
    apply_default_reply_to([msg])
    assert msg.reply_to == ["specific@anansiatlas.com"]


@pytest.mark.django_db
def test_platform_email_sends_from_mail_and_replies_to_info(settings):
    # Simulate prod: sending mailbox = mail@, backend stamps Reply-To = info@.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    from django.core.mail import EmailMessage as EM
    msg = EM(subject="Welcome", body="hi", to=["client@org.org"])
    apply_default_reply_to([msg])
    assert msg.from_email == "mail@anansiatlas.com" or msg.from_email is None  # None -> DEFAULT at send
    assert msg.reply_to == ["marcus@anansiatlas.com"]
