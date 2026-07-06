"""
Junk-email detection + cleanup for the scraped Florida market data.

The website scrape that populated FloridaOrg.contact_email sometimes captured
non-contact strings: template placeholders (user@domain.com), error-tracking
telemetry DSNs (…@sentry-next.wixpress.com), RFC-reserved example addresses,
obvious dummies (john.doe@…), and — from a scraper artifact — our own
info@anansiatlas.com. Emailing any of these bounces or loops back to us and
hurts sender reputation, so we wipe them to empty (the org keeps its phone /
website and is simply treated as "no email").
"""
JUNK_EMAIL_SUBSTRINGS = (
    "@domain.com", "user@domain", "wixpress.com", "sentry-next", "@sentry.",
    "example.com", "example.org", "example.net", "john.doe@", "jane.doe@",
    "@anansiatlas.com", "yourdomain", "youremail", "test@test", "noreply@example",
)


def is_junk_email(email: str) -> bool:
    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return bool(email)  # non-empty-but-malformed counts as junk to clear
    return any(s in e for s in JUNK_EMAIL_SUBSTRINGS)


def clean_junk_emails(queryset) -> int:
    """Blank out junk contact_email values in the queryset. Returns count cleaned."""
    cleaned = 0
    stale = []
    for org in queryset.exclude(contact_email="").iterator(chunk_size=5000):
        if is_junk_email(org.contact_email):
            org.contact_email = ""
            stale.append(org)
            cleaned += 1
        if len(stale) >= 2000:
            type(stale[0]).objects.bulk_update(stale, ["contact_email"])
            stale = []
    if stale:
        type(stale[0]).objects.bulk_update(stale, ["contact_email"])
    return cleaned
