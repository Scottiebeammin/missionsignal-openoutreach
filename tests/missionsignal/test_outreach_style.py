"""The house writing standard is shared, not copied.

Both campaigns previously carried their own Voice / Craft / What-to-avoid sections and
had already drifted — the six Craft rules were byte-identical while the Voice blocks had
diverged. These tests fail if anyone re-forks them.
"""
from __future__ import annotations

import pytest

from openoutreach.core.management.commands import (
    seed_atlas_cohort_campaign as atlas,
    seed_schools_campaign as schools,
)
from openoutreach.core.outreach_style import AUDIENCE_TOKEN, writing_standard

CAMPAIGN_DOCS = [
    pytest.param(atlas.CAMPAIGN_OBJECTIVE, "organization", id="nonprofit"),
    pytest.param(schools.CAMPAIGN_OBJECTIVE, "school", id="schools"),
]


@pytest.mark.parametrize("docs,audience", CAMPAIGN_DOCS)
def test_campaign_embeds_the_shared_standard(docs, audience):
    # Not a paraphrase, not a copy — the actual rendered text.
    assert writing_standard(audience=audience).split(AUDIENCE_TOKEN)[0][:400] in docs


@pytest.mark.parametrize("docs,audience", CAMPAIGN_DOCS)
def test_no_unsubstituted_audience_token_reaches_a_campaign(docs, audience):
    # A leaked "__AUDIENCE__" would be rendered into a real email.
    assert AUDIENCE_TOKEN not in docs


@pytest.mark.parametrize("docs,audience", CAMPAIGN_DOCS)
def test_craft_rules_appear_exactly_once(docs, audience):
    # Two copies of a rule means one of them is stale and nobody knows which.
    assert docs.count("**6. Never open two consecutive sentences") == 1
    assert docs.count("### Craft — how to make the writing better") == 1


def test_audience_noun_is_substituted_per_campaign():
    assert "any organization in the country" in writing_standard(audience="organization")
    assert "any school in the country" in writing_standard(audience="school")


def test_extra_avoid_is_appended_not_replacing_the_universal_list():
    out = writing_standard(audience="school", extra_avoid="- Education jargon.\n")
    assert "- Education jargon." in out
    assert "Any mention of price, ever, in a first cold email" in out


def test_standard_carries_the_rules_that_cost_us_a_batch():
    # Each of these was a real failure in the 12 Aug drafts. They live in the shared
    # standard now so a second campaign cannot repeat them.
    out = writing_standard()
    assert "No fake threading" in out          # "Re:" on a first cold email
    assert "pass it along yourself" in out     # backwards forwarding offer
