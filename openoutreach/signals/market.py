"""Florida Market Database logic — promote universe orgs into the sales pipeline.

The FloridaOrg table is the founder's statewide prospect UNIVERSE (all 114k+
IRS exempt organizations in Florida). Rows here are not leads; an operator
promotes one into the pipeline explicitly, which creates a SalesLead in the
cold_florida_crm segment and back-links it via FloridaOrg.promoted_lead.
"""

import re

from django.db import transaction

from openoutreach.signals.models import FloridaOrg, SalesLead

# ---------------------------------------------------------------------------
# Pure data normalizers (no DB access — unit-testable).
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-']+@[a-z0-9.\-]+\.[a-z]{2,}$")

_WEBSITE_JUNK = {
    "n/a", "na", "none", "no", "null", "www", "www.", ".", "-", "--",
    "not applicable", "unknown", "tbd", "pending", "http", "https",
    "http://", "https://",
}

# Tokens kept fully uppercase in smart_title().
_UPPER_TOKENS = {
    "LLC", "LLP", "PA", "PC", "II", "III", "IV", "VI", "VII", "USA", "US",
    "PTA", "PTO", "VFW", "AMVETS", "YMCA", "YWCA", "NAACP", "AARP", "CDC",
    "DAV", "AME", "CME", "ARC", "SPCA", "ASPCA", "FOP", "IBEW", "AFL",
    "CIO", "UMC", "SDA", "HOA", "POA", "AA", "NA", "ROTC", "JROTC", "STEM",
    "STEAM", "LGBTQ", "HBCU", "NW", "NE", "SW", "SE",
}

# Tokens re-cased to a specific natural form (matched case-insensitively).
_NATURAL_TOKENS = {
    "INC": "Inc", "CORP": "Corp", "CO": "Co", "LTD": "Ltd", "FDN": "Fdn",
    "ASSN": "Assn", "ORG": "Org", "DEPT": "Dept", "INTL": "Intl",
    "JR": "Jr", "SR": "Sr", "DR": "Dr", "MR": "Mr", "MRS": "Mrs", "MS": "Ms",
    "REV": "Rev", "ST": "St", "MT": "Mt", "FT": "Ft",
}

# Lowercase connector words when not first/last word.
_SMALL_WORDS = {"of", "and", "the", "for", "a", "an", "in", "at", "to", "on", "de", "la", "del"}


def clean_phone(raw):
    """Normalize a US phone to '(407) 555-1234'; return '' for garbage."""
    if not raw:
        return ""
    s = str(raw).strip()
    if re.search(r"[A-Za-z]", s):
        return ""
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def clean_email(raw):
    """Lowercased valid-looking email, or ''."""
    if not raw:
        return ""
    s = str(raw).strip().strip(";,").lower()
    return s if _EMAIL_RE.match(s) else ""


def clean_website(raw):
    """Normalize a website to a lowercase https:// URL; '' for junk.

    Values containing '@' are rejected here (return '') — callers may route
    them through clean_email() instead.
    """
    if not raw:
        return ""
    s = str(raw).strip().strip("\"'").lower()
    if not s or "@" in s or any(c.isspace() for c in s):
        return ""
    s = s.rstrip(".,;:!)")
    if s in _WEBSITE_JUNK:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        rest = s.split("://", 1)[1]
    else:
        rest = s
        s = "https://" + s
    rest = rest.rstrip("/")
    if not rest or "." not in rest or rest in _WEBSITE_JUNK:
        return ""
    if len(s) > 500:
        return ""
    return s


def clean_zip(raw):
    """'#####' or '#####-####' when recoverable, else the raw value."""
    if not raw:
        return raw or ""
    s = str(raw).strip()
    if re.fullmatch(r"\d{5}", s) or re.fullmatch(r"\d{5}-\d{4}", s):
        return s
    digits = re.sub(r"\D", "", s)
    if len(digits) == 9:
        return digits[:5] if digits[5:] == "0000" else f"{digits[:5]}-{digits[5:]}"
    if len(digits) == 5:
        return digits
    return s


def _cap_piece(piece):
    """Case one hyphen/slash-free piece of a word."""
    if not piece:
        return piece
    lead = ""
    while piece and not piece[0].isalnum():
        lead += piece[0]
        piece = piece[1:]
    core = piece.rstrip(".,)&")
    tail = piece[len(core):]
    if not core:
        return lead + piece
    up = core.upper()
    if up in _UPPER_TOKENS:
        return lead + up + tail
    if up in _NATURAL_TOKENS:
        return lead + _NATURAL_TOKENS[up] + tail
    if up.startswith("MC") and len(core) > 2 and core[2:].isalpha():
        return lead + "Mc" + core[2].upper() + core[3:].lower() + tail
    if len(core) > 2 and core[1] == "'" and core[0].upper() == "O":
        return lead + "O'" + core[2].upper() + core[3:].lower() + tail
    return lead + core[0].upper() + core[1:].lower() + tail


def smart_title(name):
    """Title-case ALL-CAPS or all-lowercase strings; leave mixed case alone."""
    if not name:
        return ""
    s = " ".join(str(name).split())
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return s
    all_upper = all(c.isupper() for c in letters)
    all_lower = all(c.islower() for c in letters)
    if not (all_upper or all_lower):
        return s
    words = s.split(" ")
    out = []
    last = len(words) - 1
    for i, w in enumerate(words):
        core = "".join(c for c in w if c.isalnum())
        if 0 < i < last and core.lower() in _SMALL_WORDS:
            out.append(w.lower())
            continue
        pieces = re.split(r"([-/])", w)
        out.append("".join(p if p in ("-", "/") else _cap_piece(p) for p in pieces))
    return " ".join(out)


def compact_amount(value):
    """$1.2M-style compact money label; '—' for None."""
    if value is None:
        return "—"
    n = float(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    for cut, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if n >= cut:
            v = n / cut
            label = f"{v:.1f}".rstrip("0").rstrip(".")
            return f"{sign}${label}{suffix}"
    return f"{sign}${int(n):,}"


def website_domain(url):
    """Short domain-only label for a URL ('example.org')."""
    if not url:
        return ""
    host = re.sub(r"^https?://", "", str(url)).split("/", 1)[0]
    return host[4:] if host.startswith("www.") else host


# NTEE major-group letter → service area.
_NTEE_SERVICE_AREAS = {
    "A": "Arts & Culture",
    "B": "Education",
    "C": "Environment & Animals",
    "D": "Environment & Animals",
    "E": "Health & Mental Health",
    "F": "Health & Mental Health",
    "G": "Health & Mental Health",
    "H": "Health & Mental Health",
    "I": "Crime & Legal",
    "J": "Workforce & Economic Mobility",
    "K": "Food Security",
    "L": "Homelessness & Housing",
    "M": "Public Safety",
    "N": "Recreation & Sports",
    "O": "Youth Development",
    "P": "Human Services",
    "Q": "International",
    "R": "Civil Rights",
    "S": "Community & Civic",
    "T": "Philanthropy & Grantmaking",
    "U": "Research",
    "V": "Research",
    "W": "Public Benefit",
    "X": "Faith-Based",
    "Y": "Mutual Benefit",
}

# Name-keyword fallback, checked in order (first match wins).
_NAME_KEYWORD_AREAS = [
    (("church", "ministry", "ministries", "temple", "synagogue", "mosque"), "Faith-Based"),
    (("veteran", "vfw", "amvets", "american legion"), "Veterans"),
    (("youth", "boys", "girls", "children"), "Youth Development"),
    (("school", "education", "academy", "pta"), "Education"),
    (("housing", "homeless"), "Homelessness & Housing"),
    (("food", "hunger", "pantry"), "Food Security"),
    (("health", "medical", "hospice"), "Health & Mental Health"),
    (("arts", "music", "theatre", "theater", "dance"), "Arts & Culture"),
]


def derive_service_area(ntee_code, ntee_sector, org_name):
    """Bucket an org into a service-area facet.

    Primary source: NTEE major-group letter. Fallback: keyword scan of the
    org name. Else 'Unknown'.
    """
    letter = (ntee_code or "").strip()[:1].upper()
    area = _NTEE_SERVICE_AREAS.get(letter)
    if area:
        return area
    name = (org_name or "").lower()
    for keywords, kw_area in _NAME_KEYWORD_AREAS:
        if any(k in name for k in keywords):
            return kw_area
    return "Unknown"


def _fmt_amount(value):
    return f"${value:,}" if value is not None else "unknown"


def build_provenance_notes(org: FloridaOrg) -> str:
    notes = (
        f"Promoted from Florida Market Database ({org.record_id}). "
        f"EIN: {org.ein or 'unknown'}. "
        f"NTEE: {org.ntee_code or 'unclassified'} ({org.ntee_sector or 'Unknown sector'}). "
        f"Assets: {_fmt_amount(org.asset_amount)}. Income: {_fmt_amount(org.income_amount)}. "
        f"Location: {org.city or 'unknown city'}, {org.county or 'unknown'} County."
    )
    if org.website:
        notes += f" Website: {org.website}."
    if org.principal_officer:
        notes += f" Principal officer: {org.principal_officer}."
    if org.contact_source:
        notes += f" Contact source: {org.contact_source}."
    return notes


def promote_org_to_pipeline(org: FloridaOrg, *, segment=None):
    """Create a cold SalesLead for this org, exactly once.

    ``segment`` defaults to COLD_FLORIDA_CRM; pass COLD_CALL_LIST for phone/form
    orgs with no email so they land in their own pipeline. Returns
    (lead, created); a second call is a no-op (the promoted_lead FK guards it).
    """
    segment = segment or SalesLead.Segment.COLD_FLORIDA_CRM
    with transaction.atomic():
        org = FloridaOrg.objects.select_for_update().get(pk=org.pk)
        if org.promoted_lead_id is not None:
            return org.promoted_lead, False
        lead = SalesLead.objects.create(
            name=org.name,
            organization=org.name,
            source=SalesLead.Source.COLD,
            status=SalesLead.Status.NEW,
            list_segment=segment,
            warmth=SalesLead.Warmth.COLD,
            region=org.county,
            phone=org.phone,
            email=org.contact_email,
            notes=build_provenance_notes(org),
        )
        org.promoted_lead = lead
        org.save(update_fields=["promoted_lead", "updated_at"])
    return lead, True
