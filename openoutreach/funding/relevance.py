"""Score how relevant an opportunity is to a specific organization.

Federal grants (Grants.gov) arrive with no focus_areas/beneficiaries, so a plain
keyword pull surfaces off-topic grants (e.g. "English Teaching in Brazil" for a
girls-empowerment org). This module scores each opportunity by how much its text
overlaps the org's OWN focus areas + beneficiaries + mission — so what surfaces is
tied to what the nonprofit actually does and who it serves.

When the org checks a new focus area or beneficiary (financial literacy, people
with disabilities, etc.), those keywords immediately start matching opportunities —
no code change needed; the relevance just shifts with the profile.
"""
import re

# Generic words that would match almost anything — excluded so scoring is meaningful.
_STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "into", "your", "our",
    "their", "support", "program", "programs", "services", "service", "general",
    "other", "inc", "ages", "age", "of", "to", "in", "on", "or", "at", "by", "an",
    "a", "grant", "grants", "funding", "fund", "foundation", "community", "people",
    "development", "national", "initiative", "project", "competition",
}


# Foreign-country / overseas markers — a US-domestic nonprofit can't use these grants
# even if the topic overlaps (e.g. "English Teaching for STEM in Brazil"). State Dept
# / embassy / mission grants are the usual culprits in a Grants.gov pull.
_FOREIGN_COUNTRIES = {
    "brazil", "algeria", "albania", "mexico", "india", "china", "kenya", "nigeria",
    "egypt", "ukraine", "pakistan", "afghanistan", "iraq", "jordan", "lebanon",
    "morocco", "tunisia", "colombia", "peru", "ecuador", "ghana", "ethiopia",
    "tanzania", "uganda", "vietnam", "indonesia", "philippines", "bangladesh",
    "nepal", "cambodia", "armenia", "azerbaijan", "kazakhstan", "moldova",
    "serbia", "kosovo", "bosnia", "macedonia", "turkmenistan", "uzbekistan", "mongolia",
    "rwanda", "senegal", "zambia", "zimbabwe", "malawi", "mozambique", "angola",
}
_FOREIGN_PHRASES = ("u.s. mission to", "u.s. embassy", "overseas", " abroad", "foreign assistance")

# If the grant explicitly supports US-based orgs/communities, KEEP it even when a
# foreign country is mentioned (e.g. a multinational corp's US giving program, or a
# program serving the US among other countries). US-only focus, but not at the cost
# of dropping grants that fund US nonprofits.
_US_SUPPORT_PHRASES = (
    "u.s.-based", "us-based", "u.s. based", "domestic nonprofit", "u.s. nonprofit",
    "us nonprofit", "u.s. nonprofits", "nationwide", "all 50 states",
    "across the united states", "u.s. communities", "american nonprofit",
    "501(c)(3)", "united states-based",
)


# Academic / research-grant markers — NIH/NSF studies, fellowships, scholarships,
# and university-research mechanisms a community nonprofit can't realistically pursue.
# These often match on a topic keyword ("adolescent", "youth") but are the wrong fit.
_RESEARCH_MARKERS = (
    "limited competition for the", "cognitive neuroscience", "clinical trial",
    "principal investigator", "investigator-initiated", "research project grant",
    "graduate education", "undergraduate", "postdoctoral", "doctoral",
    "fellowship", "scholarship", "abcd study", "formation of engineers",
    "biomedical research", "scientific research", "r01", "u01", "sbir", "sttr",
    "dissertation", "laboratory", "neuroimaging",
    # broadened: research/clinical centers, NIH/NSF mechanisms, defense-research pipelines
    "research center", "research institute", "post-traumatic", "epilepsy",
    "national defense education", "u24", "u54", "r21", "p20", "p30", "k23",
    "phase ii clinical", "phase iii clinical", "data coordinating center",
    "informatics and resource", "translational research", "basic research",
)


def is_research_grant(opportunity) -> bool:
    """True if the opportunity is an academic / research grant (NIH/NSF study,
    fellowship, scholarship, university mechanism) — wrong fit for a community nonprofit."""
    text = f"{opportunity.name} {opportunity.source_name or ''}".lower()
    return any(m in text for m in _RESEARCH_MARKERS)


def is_off_geography(opportunity, organization=None) -> bool:
    """True if the opportunity is tied to a foreign country / overseas post — disqualified
    for a US-domestic nonprofit. Override: kept if it explicitly supports US-based orgs."""
    text = (
        f"{opportunity.name} {opportunity.source_name or ''} "
        f"{opportunity.eligibility_notes or ''} {opportunity.notes or ''}"
    ).lower()
    if any(p in text for p in _US_SUPPORT_PHRASES):
        return False
    if any(phrase in text for phrase in _FOREIGN_PHRASES):
        return True
    return bool(set(re.findall(r"[a-z]+", text)) & _FOREIGN_COUNTRIES)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def org_keywords(organization) -> set[str]:
    """The org's relevance vocabulary — what it does + who it serves + its mission."""
    kw: set[str] = set()
    for term in list(organization.focus_areas or []) + list(organization.beneficiaries or []):
        kw |= _tokens(str(term))
    kw |= _tokens(getattr(organization, "mission", "") or "")
    return kw


def opportunity_relevance(opportunity, keywords: set[str]) -> int:
    """Count of distinct org keywords that appear in the opportunity's text.

    0 = no overlap (off-topic — kept out of the top recommendations).
    """
    if not keywords:
        return 0
    parts = [
        opportunity.name,
        opportunity.notes,
        opportunity.eligibility_notes,
        opportunity.source_name,
    ]
    parts += [str(x) for x in (opportunity.focus_areas or [])]
    parts += [str(x) for x in (opportunity.beneficiaries or [])]
    opp_tokens = _tokens(" ".join(p for p in parts if p))
    return len(keywords & opp_tokens)
