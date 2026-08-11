"""The State & Local section — local money on its own terms.

Local sources were competing in the federal ranking and losing. `opportunity_
relevance` scores keyword overlap, so a Grants.gov notice with a descriptive
title and pages of eligibility prose always outscores "City of Orlando —
Community Investment Program", which is four words and a URL. The first fix was
a relevance floor; it shipped invisible twice, because any floor is calibrated
against one organization's score histogram and the next client's is different.

This is the durable version: local sources stop competing at all. They are
grouped by the jurisdiction that issued them — state, then county, then city —
and rendered in their own section, so a $5,000 county fund sits next to a
$25,000 state pass-through instead of being compared to a $7.5M NSF programme.

Nothing here is Florida-specific. Jurisdictions come from the organization's own
state/county/city and the registry in funding.local_sources, so an org in Georgia
gets a Georgia section the moment Georgia sources are registered — and an honest
empty state until then. The three empty states are deliberately different, because
they need three different actions from three different people:

  no geography on file   -> the client sets it in Settings
  geography, no sources  -> we register sources for that state
  sources, nothing saved -> someone runs pull_local_grants

A section that said "nothing here" to all three would hide two of them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from openoutreach.funding.local_sources import CITY, COUNTY, STATE, sources_for_organization
from openoutreach.funding.models import Opportunity

# Broadest first: a state pass-through is usually the largest award and the
# longest lead time, and a client reading top-down should meet it first.
_LEVEL_ORDER = {STATE: 0, COUNTY: 1, CITY: 2}


@dataclass
class LocalSourceGroup:
    """One registered source and whatever has been ingested from it."""

    source: object                      # LocalSource
    opportunities: list = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return bool(getattr(self.source, "blocked", ""))

    @property
    def name(self) -> str:
        return self.source.name

    @property
    def url(self) -> str:
        return self.source.url

    @property
    def count(self) -> int:
        return len(self.opportunities)


@dataclass
class LocalJurisdiction:
    """All sources at one level of government — "Florida", "Orange County"."""

    level: str
    label: str
    groups: list[LocalSourceGroup] = field(default_factory=list)

    @property
    def opportunity_count(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def reachable_groups(self) -> list[LocalSourceGroup]:
        return [g for g in self.groups if not g.is_blocked]

    @property
    def blocked_groups(self) -> list[LocalSourceGroup]:
        return [g for g in self.groups if g.is_blocked]


@dataclass
class LocalOverview:
    jurisdictions: list[LocalJurisdiction] = field(default_factory=list)
    opportunity_total: int = 0
    source_total: int = 0
    blocked_total: int = 0
    # Which of county/city the org hasn't told us — each one silently costs it
    # every source registered at that level.
    missing_geography: list[str] = field(default_factory=list)
    state: str = ""
    has_state: bool = True

    @property
    def state_label(self) -> str:
        return self.state or "your area"

    @property
    def empty_reason(self) -> str:
        """Which of the three empty states this is, or "" when there's content.

        The template branches on this rather than on counts, so the distinction
        between "we have no sources for this state" and "nobody has run the
        ingest" can't collapse into one message.
        """
        if not self.has_state:
            return "no_geography"
        if not self.source_total:
            return "no_sources_registered"
        if not self.opportunity_total:
            return "not_yet_ingested"
        return ""


def local_opportunities(project):
    """Every ingested state/county/city row for this project."""
    return list(
        Opportunity.objects.filter(
            project=project, external_id__startswith="localgov:",
        ).exclude(
            status__in=[Opportunity.Status.EXPIRED, Opportunity.Status.ARCHIVED],
        )
    )


def _by_source_url(opportunities) -> dict[str, list]:
    """Index rows by the registry URL they were ingested from.

    Both candidate builders in local_sources stamp source_url = source.url, and
    grounding persists it as source_urls[0], so this is an exact join rather than
    a name match — the source can be renamed without orphaning its rows.
    """
    index: dict[str, list] = {}
    for opp in opportunities:
        for url in (opp.source_urls or []):
            index.setdefault(url, []).append(opp)
    return index


def _label_for(level: str, organization) -> str:
    if level == STATE:
        return organization.state or "State"
    if level == COUNTY:
        county = (organization.county or "").strip()
        # "Orange County", not "Orange County County".
        return county if county.lower().endswith("county") else f"{county} County"
    return (organization.city or "City").strip()


def build_local_overview(project) -> LocalOverview:
    """Group this organization's local money by the government that issues it."""
    organization = project.organization
    state = (organization.state or "").strip()
    if not state:
        return LocalOverview(has_state=False, missing_geography=["state"])

    # Blocked sources are included on purpose: a source we know exists and cannot
    # currently reach is information the client should have, not an absence.
    sources = sources_for_organization(organization, include_blocked=True)
    index = _by_source_url(local_opportunities(project))

    buckets: dict[str, LocalJurisdiction] = {}
    for source in sources:
        jurisdiction = buckets.get(source.level)
        if jurisdiction is None:
            jurisdiction = LocalJurisdiction(
                level=source.level, label=_label_for(source.level, organization),
            )
            buckets[source.level] = jurisdiction
        jurisdiction.groups.append(
            LocalSourceGroup(source=source, opportunities=index.get(source.url, []))
        )

    jurisdictions = sorted(buckets.values(), key=lambda j: _LEVEL_ORDER.get(j.level, 9))
    for jurisdiction in jurisdictions:
        # Sources with rows first, then blocked ones last — a gap shouldn't head
        # a section that has real money in it.
        jurisdiction.groups.sort(key=lambda g: (g.is_blocked, -g.count, g.name))

    missing = [
        level for level, value in (("county", organization.county), ("city", organization.city))
        if not (value or "").strip()
    ]
    return LocalOverview(
        jurisdictions=jurisdictions,
        opportunity_total=sum(j.opportunity_count for j in jurisdictions),
        source_total=sum(len(j.groups) for j in jurisdictions),
        blocked_total=sum(len(j.blocked_groups) for j in jurisdictions),
        missing_geography=missing,
        state=state,
    )
