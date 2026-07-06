"""
Deliverability smoke test. Sends ONE real email through the live email backend
to an address you control, mirroring exactly how a cold outreach email is sent
(from mail@, BCC marcus@, Reply-To marcus@), so you can confirm it lands in the
inbox — not spam — BEFORE sending the real cold batch to actual orgs.

    python manage.py send_test_email you@yourgmail.com

Then check that inbox: if it arrives and sits in the inbox with the right From/
Reply-To, the pipeline works end-to-end. If it bounces, errors, or lands in
spam, stop and fix before sending to real orgs. A copy also BCCs marcus@, so a
successful send drops a copy in Marcus's inbox too (same as every cold send).
"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.notifications import MARCUS_EMAIL


class Command(BaseCommand):
    help = "Send one deliverability test email through the live backend (mirrors a cold send)."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient address you control (check it after).")
        parser.add_argument("--from-email", default=settings.DEFAULT_FROM_EMAIL,
                            help="Override the From (defaults to the cold sender, mail@).")

    def handle(self, *args, **options):
        to = options["to"].strip()
        if "@" not in to:
            raise CommandError(f"'{to}' is not an email address.")
        from_email = options["from_email"]
        bcc = [MARCUS_EMAIL] if MARCUS_EMAIL.lower() != to.lower() else None

        message = EmailMessage(
            subject="Anansi Atlas — deliverability test",
            body=(
                "This is a one-off test send from the Anansi Atlas outreach system.\n\n"
                "If you're reading this in your inbox (not spam), the cold-email pipeline\n"
                "works end-to-end: SMTP auth, From, Reply-To, and BCC are all wired correctly.\n\n"
                f"From:     {from_email}\n"
                f"Reply-To: stamped by the backend (should be {MARCUS_EMAIL})\n"
                "— Anansi Atlas"
            ),
            from_email=from_email,
            to=[to],
            bcc=bcc,
        )
        try:
            sent = message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(
                f"Send FAILED: {exc}\n"
                "The SMTP settings (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL) "
                "are likely missing or wrong on this environment — fix them before the cold batch."
            )
        self.stdout.write(self.style.SUCCESS(
            f"Sent {sent} test email to {to} from {from_email} (BCC {MARCUS_EMAIL}).\n"
            f"Now open {to} and confirm it's in the INBOX (not spam), then check marcus@ for the BCC copy.\n"
            "Inbox on both → you're clear to send the cold batch."
        ))
