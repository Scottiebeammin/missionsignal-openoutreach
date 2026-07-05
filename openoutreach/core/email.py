"""
Email backend that stamps a default Reply-To on every outbound message.

The platform sends FROM the dedicated sending mailbox (DEFAULT_FROM_EMAIL, e.g.
mail@anansiatlas.com) so mail is DKIM-signed by that Google Workspace account,
but a client hitting "reply" should reach the human inbox we actually read.
This backend sets Reply-To to REPLY_TO_EMAIL (default info@anansiatlas.com) on
any message that doesn't already specify one — one central place, so every
current and future email inherits it without touching call sites.
"""
import os

from django.core.mail.backends.smtp import EmailBackend as _SMTPBackend

DEFAULT_REPLY_TO = "marcus@anansiatlas.com"


def reply_to_address() -> str:
    return os.getenv("REPLY_TO_EMAIL", DEFAULT_REPLY_TO)


def apply_default_reply_to(email_messages):
    """Set Reply-To on every message that lacks one. Mutates in place."""
    address = reply_to_address()
    for message in email_messages:
        if not getattr(message, "reply_to", None):
            message.reply_to = [address]
    return email_messages


class ReplyToSMTPBackend(_SMTPBackend):
    def send_messages(self, email_messages):
        return super().send_messages(apply_default_reply_to(email_messages))
