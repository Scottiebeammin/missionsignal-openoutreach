"""IRS 990-PF foundation grant intelligence (grounded discovery, Layer 1).

Parses private-foundation 990-PF e-file returns (Part XV grants paid) into
``FoundationGrantPaid`` rows and derives verified ``Funder`` records from the
aggregate giving history. Every derived fact traces to an authoritative IRS
XML bundle URL — the same no-hallucination standard as ``grants_gov.py``.

Stdlib-only parsing (xml.etree), no network in this module: downloading and
streaming the bundles is ``manage.py pull_990pf_grants`` +
``funding/irs_xml.py``.
"""

import hashlib
import re
import xml.etree.ElementTree as ET
from collections import Counter

from django.utils import timezone

from openoutreach.funding.models import FoundationGrantPaid, Funder

# 2-letter recipient/filer state codes -> full names, so derived Funder
# geography matches the vocabulary the matching engine sees elsewhere
# ("Florida", not "FL").
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico",
}

# Grant-purpose keywords -> service-area cause vocabulary (the same facet
# values FloridaOrg.service_area uses, so derived funder focus areas line up
# with org profiles in matching). Word-boundary matched, case-insensitive.
PURPOSE_CAUSE_KEYWORDS = [
    ("Youth Development", (
        "youth", "children", "boys & girls", "boys and girls", "mentoring",
        "after school", "after-school", "juvenile",
    )),
    ("Education", (
        "education", "educational", "school", "schools", "scholarship",
        "scholarships", "literacy", "stem", "tuition", "university", "college",
    )),
    ("Health & Mental Health", (
        "health", "healthcare", "medical", "hospital", "hospitals", "mental",
        "cancer", "hospice", "clinic", "clinics", "wellness", "disease",
    )),
    ("Homelessness & Housing", (
        "homeless", "homelessness", "housing", "shelter", "shelters",
    )),
    ("Workforce & Economic Mobility", (
        "workforce", "job training", "employment", "economic mobility",
        "economic development", "entrepreneurship", "financial literacy",
    )),
    ("Food Security", (
        "food", "hunger", "meals", "nutrition", "pantry", "feeding",
    )),
    ("Arts & Culture", (
        "arts", "art", "museum", "museums", "music", "theatre", "theater",
        "cultural", "culture", "dance", "ballet", "orchestra",
    )),
    ("Faith-Based", (
        "church", "churches", "ministry", "ministries", "faith", "religious",
        "religion", "synagogue", "temple", "diocese", "parish",
    )),
    ("Veterans", (
        "veteran", "veterans", "military",
    )),
    ("Human Services", (
        "human services", "social services", "family services",
        "community services", "disability", "disabilities", "elderly", "seniors",
    )),
]

_DERIVED_NOTE_PREFIX = "Derived from IRS 990-PF filings:"


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _find_local(elem, *path):
    """Walk children by local (namespace-stripped) tag names. None if absent."""
    node = elem
    for name in path:
        node = next((child for child in node if _local(child.tag) == name), None)
        if node is None:
            return None
    return node


def _text_local(elem, *path):
    node = _find_local(elem, *path)
    return (node.text or "").strip() if node is not None else ""


def _clean_ein(value):
    """Digits only, zero-padded to the canonical 9. '' when unusable."""
    digits = re.sub(r"\D", "", value or "")
    return digits.zfill(9)[:9] if digits else ""


def _business_name(elem):
    """BusinessNameLine1(+2) text under elem joined with a space, else ''.

    IRS names routinely wrap onto the second line ('DAVID E RETIK AND
    CHRISTOPHER D MELLO' / 'FOUNDATION') — dropping it truncates the name.
    """
    if elem is None:
        return ""
    lines = {"1": "", "2": ""}
    for child in elem.iter():
        m = re.fullmatch(r"BusinessNameLine([12])(?:Txt)?", _local(child.tag))
        if m and not lines[m.group(1)]:
            lines[m.group(1)] = (child.text or "").strip()
    return " ".join(part for part in (lines["1"], lines["2"]) if part)


def _us_address(elem):
    """(city, state) from the first *USAddress child of elem, else ('', '')."""
    if elem is None:
        return "", ""
    for child in elem:
        if _local(child.tag).endswith("USAddress"):
            return (
                _text_local(child, "CityNm") or _text_local(child, "City"),
                (_text_local(child, "StateAbbreviationCd")
                 or _text_local(child, "State")).upper()[:2],
            )
    return "", ""


def parse_990pf_grants(xml_bytes):
    """Parse one e-file return XML (bytes) -> dict or None.

    None when the bytes aren't XML, aren't a 990-PF return (no
    ``ReturnData/IRS990PF``), or carry no filer EIN. Otherwise::

        {filer_ein, filer_name, filer_city, filer_state, tax_year,
         grants: [{recipient_name, recipient_ein, recipient_city,
                   recipient_state, amount, purpose}, ...]}

    Namespace-agnostic (matches on local tag names), mirroring
    ``fetch_990_contacts.parse_990_xml``.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    if not any(_local(el.tag) == "IRS990PF" for el in root.iter()):
        return None

    filer_ein = filer_name = filer_city = filer_state = tax_year = ""
    for el in root.iter():
        tag = _local(el.tag)
        if tag == "Filer" and not filer_ein:
            filer_ein = _clean_ein(_text_local(el, "EIN"))
            filer_name = _business_name(_find_local(el, "BusinessName")) or _business_name(el)
            filer_city, filer_state = _us_address(el)
        elif tag == "TaxYr" and not tax_year:
            tax_year = (el.text or "").strip()
    if not filer_ein:
        return None

    grants = []
    for grp in root.iter():
        if _local(grp.tag) != "GrantOrContributionPdDurYrGrp":
            continue
        recipient_name = (
            _business_name(_find_local(grp, "RecipientBusinessName"))
            or _text_local(grp, "RecipientPersonNm")
        )
        recipient_city, recipient_state = _us_address(grp)
        amount_text = re.sub(r"[^\d-]", "", _text_local(grp, "Amt"))
        try:
            amount = int(amount_text)
        except ValueError:
            amount = None
        grants.append({
            "recipient_name": recipient_name[:500],
            "recipient_ein": _clean_ein(_text_local(grp, "RecipientEINTxt")),
            "recipient_city": recipient_city[:120],
            "recipient_state": recipient_state,
            "amount": amount,
            "purpose": _text_local(grp, "GrantOrContributionPurposeTxt"),
        })

    return {
        "filer_ein": filer_ein,
        "filer_name": filer_name[:500],
        "filer_city": filer_city[:120],
        "filer_state": filer_state,
        "tax_year": tax_year[:4],
        "grants": grants,
    }


def grant_dedup_key(filer_ein, tax_year, recipient_name, amount):
    """sha256 over (filer_ein, tax_year, recipient_name.lower(), amount)."""
    basis = "|".join([
        filer_ein or "",
        str(tax_year or ""),
        (recipient_name or "").lower().strip(),
        "" if amount is None else str(amount),
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def florida_relevant_grants(parsed):
    """The subset of a parsed return's grants worth storing: FL filer keeps
    everything (its giving footprint is the intelligence); non-FL filers keep
    only their FL-recipient grants."""
    if parsed["filer_state"] == "FL":
        return list(parsed["grants"])
    return [g for g in parsed["grants"] if g["recipient_state"] == "FL"]


def store_grants(parsed, source_url):
    """Upsert one parsed return's Florida-relevant grants. -> {created, skipped}.

    Idempotent on ``dedup_key`` (existing rows are skipped, never rewritten).
    """
    rows, keys = [], set()
    for grant in florida_relevant_grants(parsed):
        key = grant_dedup_key(
            parsed["filer_ein"], parsed["tax_year"], grant["recipient_name"], grant["amount"],
        )
        if key in keys:  # duplicate line inside the same return
            continue
        keys.add(key)
        rows.append(FoundationGrantPaid(
            filer_ein=parsed["filer_ein"],
            filer_name=parsed["filer_name"],
            filer_city=parsed["filer_city"],
            filer_state=parsed["filer_state"],
            recipient_name=grant["recipient_name"],
            recipient_ein=grant["recipient_ein"],
            recipient_city=grant["recipient_city"],
            recipient_state=grant["recipient_state"],
            amount=grant["amount"],
            purpose=grant["purpose"],
            tax_year=parsed["tax_year"],
            source_url=source_url[:500],
            dedup_key=key,
        ))
    if not rows:
        return {"created": 0, "skipped": 0}
    existing = set(
        FoundationGrantPaid.objects.filter(dedup_key__in=keys)
        .values_list("dedup_key", flat=True)
    )
    fresh = [row for row in rows if row.dedup_key not in existing]
    FoundationGrantPaid.objects.bulk_create(fresh, ignore_conflicts=True)
    return {"created": len(fresh), "skipped": len(rows) - len(fresh)}


# ---- Funder derivation ------------------------------------------------------

def _display_name(raw):
    """IRS ALL-CAPS name -> title case ('THE SMITH FAM FOUNDATION' style)."""
    name = re.sub(r"\s+", " ", (raw or "")).strip()
    if name.isupper():
        name = name.title().replace("'S", "'s")
    return name


def focus_areas_from_purposes(purposes, cap=5):
    """Map grant-purpose texts through the cause-area keyword vocabulary.

    Returns cause areas ordered by how many purposes mention them (cap 5).
    """
    counts = Counter()
    for purpose in purposes:
        text = (purpose or "").casefold()
        if not text:
            continue
        for area, keywords in PURPOSE_CAUSE_KEYWORDS:
            if any(re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text)
                   for kw in keywords):
                counts[area] += 1
    return [area for area, _ in counts.most_common(cap)]


def _funder_ein(external_ids):
    """The irs-ein recorded in a Funder.external_ids blob (either shape), or ''."""
    if isinstance(external_ids, dict):
        return str(external_ids.get("irs-ein", "") or "")
    if isinstance(external_ids, list):
        for entry in external_ids:
            if isinstance(entry, dict) and entry.get("system") == "irs-ein":
                return str(entry.get("id", "") or "")
    return ""


def _derived_note(stats):
    top = ", ".join(stats["top_recipients"]) or "n/a"
    years = (stats["year_min"] if stats["year_min"] == stats["year_max"]
             else f"{stats['year_min']}-{stats['year_max']}")
    return (
        f"{_DERIVED_NOTE_PREFIX} {stats['count']} grants, ${stats['total']:,} total, "
        f"years {years}. Top recipients: {top}."
    )


def _apply_derived_note(existing_notes, note):
    """Append the derived line, or refresh a previously-appended one in place."""
    if _DERIVED_NOTE_PREFIX in existing_notes:
        return re.sub(
            rf"{re.escape(_DERIVED_NOTE_PREFIX)}[^\n]*", lambda _m: note,
            existing_notes, count=1,
        )
    return f"{existing_notes.rstrip()}\n\n{note}".strip()


def _foundation_stats(grants):
    """Aggregate one filer's FoundationGrantPaid rows into derivation inputs."""
    grants = list(grants)
    latest = max(grants, key=lambda g: g.tax_year)
    years = sorted({g.tax_year for g in grants if g.tax_year})
    by_amount = sorted(grants, key=lambda g: g.amount or 0, reverse=True)
    top_recipients, seen = [], set()
    for grant in by_amount:
        name = _display_name(grant.recipient_name)
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            top_recipients.append(name)
        if len(top_recipients) == 3:
            break
    geography, geo_seen = [], set()
    for grant in grants:  # states first — the coarse footprint
        state = STATE_NAMES.get(grant.recipient_state)
        if state and state.casefold() not in geo_seen:
            geo_seen.add(state.casefold())
            geography.append(state)
    for grant in grants:
        city = _display_name(grant.recipient_city)
        if city and city.casefold() not in geo_seen and len(geography) < 10:
            geo_seen.add(city.casefold())
            geography.append(city)
    return {
        "name": _display_name(latest.filer_name),
        "count": len(grants),
        "total": sum(g.amount or 0 for g in grants),
        "year_min": years[0] if years else "",
        "year_max": years[-1] if years else "",
        "top_recipients": top_recipients,
        "geography": geography[:10],
        # Purposes are primary; when they're all generic ("GENERAL OPERATING
        # SUPPORT"), recipient names are an equally grounded fallback signal
        # ("SHRINERS HOSPITALS FOR CHILDREN" -> Health & Mental Health).
        "focus_areas": (
            focus_areas_from_purposes([g.purpose for g in grants])
            or focus_areas_from_purposes([g.recipient_name for g in grants])
        ),
        "source_urls": sorted({g.source_url for g in grants if g.source_url})[:5],
    }


def derive_foundation_funders(min_grants=3):
    """Upsert global Funder rows from aggregated 990-PF giving history.

    Foundations with >= ``min_grants`` stored (Florida-relevant) grants become
    verified ``Funder`` records — provably traced to IRS filings, the same
    standard as grants.gov rows. Existing funders (matched by irs-ein external
    id, else exact name) are never clobbered: blanks are filled, the
    990-PF-derived note is appended/refreshed, and the grounded giving stats
    (``grant_count``, ``grants_total_amount``) are refreshed — nothing else is
    touched. ``is_derived`` marks rows this derivation *created* (recognized on
    re-runs by notes that start with the derived-note prefix); curated funders
    that derivation merely enriches keep ``is_derived=False`` so the matching
    pool always scores them. Re-running is therefore also the backfill path
    for the quality fields (``pull_990pf_grants --skip-pull --derive-funders``).

    Returns {"created": n, "updated": n, "considered": n}.
    """
    by_ein = {}
    for grant in FoundationGrantPaid.objects.all().iterator(chunk_size=2000):
        by_ein.setdefault(grant.filer_ein, []).append(grant)
    eligible = {ein: g for ein, g in by_ein.items() if len(g) >= min_grants}

    ein_index, name_index = {}, {}
    for funder in Funder.objects.all():
        ein = _funder_ein(funder.external_ids)
        if ein:
            ein_index.setdefault(ein, funder)
        name_index.setdefault(funder.name.casefold().strip(), funder)

    created = updated = 0
    for ein, grants in sorted(eligible.items()):
        stats = _foundation_stats(grants)
        note = _derived_note(stats)
        external_ids = [{"system": "irs-ein", "id": ein}]
        funder = ein_index.get(ein) or name_index.get(stats["name"].casefold())

        if funder is None:
            funder = Funder.objects.create(
                name=stats["name"][:500],
                funder_type=Funder.FunderType.FAMILY_FOUNDATION,
                geography=stats["geography"],
                focus_areas=stats["focus_areas"],
                notes=note,
                source_urls=stats["source_urls"],
                external_ids=external_ids,
                verification_status=Funder.VerificationStatus.VERIFIED,
                last_reviewed_at=timezone.now(),
                active=True,
                grant_count=stats["count"],
                grants_total_amount=stats["total"],
                is_derived=True,
            )
            ein_index[ein] = funder
            name_index.setdefault(funder.name.casefold().strip(), funder)
            created += 1
            continue

        # Existing funder: fill blanks + append/refresh the derived note and
        # the grounded giving stats. Human-edited name/type/geography/focus
        # areas are never overwritten. A row whose notes START with the
        # derived-note prefix was created by an earlier derivation run — flag
        # it is_derived so re-running doubles as the backfill; curated rows
        # (human notes first, note appended after) stay is_derived=False.
        if (funder.notes or "").lstrip().startswith(_DERIVED_NOTE_PREFIX):
            funder.is_derived = True
        funder.grant_count = stats["count"]
        funder.grants_total_amount = stats["total"]
        if not funder.geography:
            funder.geography = stats["geography"]
        if not funder.focus_areas:
            funder.focus_areas = stats["focus_areas"]
        if not _funder_ein(funder.external_ids):
            if isinstance(funder.external_ids, list) and funder.external_ids:
                funder.external_ids = funder.external_ids + external_ids
            elif isinstance(funder.external_ids, dict) and funder.external_ids:
                funder.external_ids = {**funder.external_ids, "irs-ein": ein}
            else:
                funder.external_ids = external_ids
        merged_urls = list(funder.source_urls or [])
        merged_urls += [u for u in stats["source_urls"] if u not in merged_urls]
        funder.source_urls = merged_urls
        funder.notes = _apply_derived_note(funder.notes or "", note)
        if funder.verification_status == Funder.VerificationStatus.UNVERIFIED:
            # Upgrade only from the default; human review states are theirs.
            funder.verification_status = Funder.VerificationStatus.VERIFIED
        funder.save()
        updated += 1

    return {"created": created, "updated": updated, "considered": len(eligible)}
