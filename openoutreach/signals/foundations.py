"""
Private-foundation intelligence for the client portal (Ecosystem → Foundations).

Two grounded layers, both IRS-traceable:
- Matched foundations: 990-PF-derived (plus curated) foundation Funders whose
  focus overlaps the org's areas of support, drawn through the same
  performance-guarded pool the matching engine uses (curated always in,
  derived prefiltered + capped).
- Receipts: actual FoundationGrantPaid rows paid to organizations LIKE this
  one — same service area, same county when known. Proof, not prediction.
  Page-load joins use an exact-name SQL match against the Florida market DB
  (the offline ``grants_to_orgs_like`` python-normalized join is too slow for
  a request), so this panel is a floor, not a ceiling — labeled as such.

"Track" wires a foundation back into the opportunity field: one click creates
a project-scoped Opportunity (``external_id="funder:<pk>"``, idempotent) that
flows into Top Picks / Pipeline with a workspace like any other grant.
"""
from dataclasses import dataclass

from openoutreach.funding.models import FoundationGrantPaid, Funder, Opportunity
from openoutreach.signals.demo_guard import exclude_demo
from openoutreach.signals.matching import funder_matching_pool

FOUNDATION_TYPES = (
    Funder.FunderType.COMMUNITY_FOUNDATION,
    Funder.FunderType.CORPORATE_FOUNDATION,
    Funder.FunderType.FAMILY_FOUNDATION,
)

# Canonical focus categories → FloridaOrg.service_area vocabulary (NTEE-derived).
_SERVICE_AREA_MAP = {
    "youth development": "Youth Development",
    "girls empowerment": "Youth Development",
    "mentorship": "Youth Development",
    "life skills": "Youth Development",
    "education": "Education",
    "education support": "Education",
    "digital equity": "Community & Civic",
    "workforce development": "Workforce & Economic Mobility",
    "career readiness": "Workforce & Economic Mobility",
    "small business": "Workforce & Economic Mobility",
    "economic mobility": "Workforce & Economic Mobility",
    "healthcare": "Health & Mental Health",
    "mental health": "Health & Mental Health",
    "health and wellness": "Health & Mental Health",
    "food security": "Food Security",
    "housing": "Homelessness & Housing",
    "homelessness": "Homelessness & Housing",
    "arts & culture": "Arts & Culture",
    "community development": "Community & Civic",
    "community service": "Community & Civic",
    "rural communities": "Community & Civic",
    "environmental justice": "Environment & Animals",
    "veterans": "Veterans",
    "senior services": "Human Services",
    "disability": "Human Services",
    "immigrant / refugee support": "Human Services",
    "lgbtq+": "Civil Rights",
    "gender equity": "Civil Rights",
    "reentry / justice-involved": "Crime & Legal",
}


def service_areas_for(focus_areas) -> list[str]:
    seen, areas = set(), []
    for focus in focus_areas or []:
        mapped = _SERVICE_AREA_MAP.get(str(focus).casefold())
        if mapped and mapped not in seen:
            seen.add(mapped)
            areas.append(mapped)
    return areas


@dataclass
class FoundationMatch:
    funder: Funder
    overlap: list[str]
    total_display: str = ""
    tracked_opportunity_id: int | None = None


# Rough "a grant this size could be us" target by annual budget. Foundation
# grants to a nonprofit typically land well under its annual budget; these
# targets center the band so the receipts panel leads with relatable grants
# instead of $2M university gifts. Keys match Organization.budget_range values
# (freeform across intake versions — matched case/space-insensitively).
_BUDGET_TARGET = [
    ("5m", 1_000_000),
    ("1m - 5m", 400_000),
    ("1m-5m", 400_000),
    ("250k - 1m", 100_000),
    ("250k-1m", 100_000),
    ("under_250k", 25_000),
    ("under $250k", 25_000),
    ("250k", 25_000),
]


def budget_target_amount(budget_range: str) -> int | None:
    key = (budget_range or "").strip().casefold()
    if not key:
        return None
    for needle, target in _BUDGET_TARGET:
        if needle in key:
            return target
    return None


@dataclass
class GrantReceipt:
    filer_name: str
    recipient_name: str
    amount_display: str
    tax_year: int | None
    purpose: str


@dataclass
class FoundationOverview:
    matches: list[FoundationMatch]
    receipts: list[GrantReceipt]
    receipt_count: int
    receipt_total_display: str
    receipt_foundation_count: int
    service_areas: list[str]
    county: str
    sort: str = "fit"           # "fit" (grants your size) | "largest"
    fit_available: bool = False  # a budget target exists, so the toggle is meaningful


def _money(amount) -> str:
    return f"${amount:,.0f}" if amount else ""


def build_foundation_overview(project, *, limit=12, grants_limit=15, sort="fit") -> FoundationOverview:
    organization = project.organization
    focus_terms = [str(a) for a in (organization.focus_areas or [])]
    base = exclude_demo(Funder.objects.filter(active=True, funder_type__in=FOUNDATION_TYPES))
    pool = funder_matching_pool(focus_terms, base=base)

    focus_cf = [t.casefold() for t in focus_terms if len(t) >= 3]
    matches = []
    for funder in pool:
        overlap = []
        for area in (funder.focus_areas or []):
            area_cf = str(area).casefold()
            if any(term in area_cf or area_cf in term for term in focus_cf):
                overlap.append(str(area))
        if overlap or not funder.is_derived:
            matches.append(FoundationMatch(
                funder=funder,
                overlap=overlap[:4],
                total_display=_money(funder.grants_total_amount),
            ))
    matches.sort(key=lambda m: (-len(m.overlap), -(m.funder.grant_count or 0), m.funder.name.casefold()))
    matches = matches[:limit]

    tracked = {
        external_id: opportunity_id
        for opportunity_id, external_id in Opportunity.objects.filter(
            project=project, external_id__startswith="funder:",
        ).values_list("pk", "external_id")
    }
    for match in matches:
        match.tracked_opportunity_id = tracked.get(f"funder:{match.funder.pk}")

    service_areas = service_areas_for(focus_terms)
    county = (organization.county or "").strip()
    receipts, receipt_count, receipt_total, foundation_count = [], 0, 0, 0
    if service_areas:
        from openoutreach.signals.models import FloridaOrg

        org_names = FloridaOrg.objects.filter(service_area__in=service_areas)
        if county:
            org_names = org_names.filter(county=county)
        names = list(org_names.values_list("name", flat=True)[:2000])
        name_variants = {n for n in names} | {n.upper() for n in names}
        grants = (
            FoundationGrantPaid.objects.filter(recipient_name__in=name_variants)
            .exclude(amount=None)
        )
        from django.db.models import Sum

        receipt_count = grants.count()
        totals = grants.aggregate(total=Sum("amount"))
        receipt_total = totals["total"] or 0
        foundation_count = grants.values("filer_ein").distinct().count()

        target = budget_target_amount(organization.budget_range)
        fit_available = target is not None
        if sort == "fit" and target:
            # Lead with grants closest to what an org this size actually receives,
            # not the biggest institutional gifts. Bounded window kept in python.
            window = list(grants.order_by("-amount")[:400])
            window.sort(key=lambda g: abs((g.amount or 0) - target))
            shown = window[:grants_limit]
        else:
            sort = "largest"
            shown = list(grants.order_by("-amount")[:grants_limit])
        receipts = [
            GrantReceipt(
                filer_name=g.filer_name.title(),
                recipient_name=g.recipient_name.title(),
                amount_display=_money(g.amount),
                tax_year=g.tax_year,
                purpose=(g.purpose or "")[:140],
            )
            for g in shown
        ]

    return FoundationOverview(
        matches=matches,
        receipts=receipts,
        receipt_count=receipt_count,
        receipt_total_display=_money(receipt_total),
        receipt_foundation_count=foundation_count,
        service_areas=service_areas,
        county=county,
        sort=sort if sort in ("fit", "largest") else "fit",
        fit_available=fit_available,
    )
