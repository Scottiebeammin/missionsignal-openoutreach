"""The house writing standard is shared, not copied.

Both campaigns previously carried their own Voice / Craft / What-to-avoid sections and
had already drifted — the six Craft rules were byte-identical while the Voice blocks had
diverged. These tests fail if anyone re-forks them.

Deliberately asserting on INVARIANTS, not on prose. The standard is designed to be
swapped wholesale, so a test that pins exact wording fails on every rewrite and teaches
people to delete tests. The durable facts are: the campaigns embed the rendered standard
verbatim, exactly once, with the audience noun substituted.
"""
from __future__ import annotations

import pytest

from openoutreach.core.management.commands import (
    seed_atlas_cohort_campaign as atlas,
    seed_schools_campaign as schools,
)
from openoutreach.core.outreach_style import AUDIENCE_TOKEN, writing_standard

CAMPAIGNS = [
    pytest.param(atlas.CAMPAIGN_OBJECTIVE, "organization", id="nonprofit"),
    pytest.param(schools.CAMPAIGN_OBJECTIVE, "school", id="schools"),
]


@pytest.mark.parametrize("docs,audience", CAMPAIGNS)
def test_campaign_embeds_the_rendered_standard_verbatim(docs, audience):
    # Containment of the whole rendered text — a paraphrase or a partial copy fails.
    assert writing_standard(audience=audience) in docs


@pytest.mark.parametrize("docs,audience", CAMPAIGNS)
def test_standard_appears_exactly_once(docs, audience):
    # Two copies of a rule means one is stale and nobody knows which.
    assert docs.count(writing_standard(audience=audience)) == 1


@pytest.mark.parametrize("docs,audience", CAMPAIGNS)
def test_no_unsubstituted_token_reaches_a_campaign(docs, audience):
    # A leaked "__AUDIENCE__" would render into a real email.
    assert AUDIENCE_TOKEN not in docs


def test_audience_noun_differs_between_campaigns():
    org, school = writing_standard("organization"), writing_standard("school")
    assert org != school
    assert AUDIENCE_TOKEN not in org and AUDIENCE_TOKEN not in school
    assert "organization" in org and "school" in school


def test_extra_avoid_is_appended_without_replacing_the_standard():
    base = writing_standard(audience="school")
    out = writing_standard(audience="school", extra_avoid="- Education jargon.\n")
    assert base in out                      # nothing dropped
    assert out.endswith("- Education jargon.")


@pytest.mark.parametrize("docs,audience", CAMPAIGNS)
def test_every_campaign_gets_the_self_check(docs, audience):
    # The self-check is the only part that enforces the rest — a campaign that embedded
    # the voice rules but lost the check would fail silently and look fine.
    assert "Self-check" in docs


def test_standard_bans_the_two_failures_that_cost_us_a_batch():
    # 12 Aug: two drafts opened "Re:" on first contact, two offered to pass the email
    # along to someone the sender doesn't know. Asserting on the trigger tokens rather
    # than the sentence, so a rewording doesn't break this but a deletion does.
    out = writing_standard()
    assert '"Re:"' in out and '"Fwd:"' in out
    assert "pass this along" in out


@pytest.mark.parametrize("docs,audience", [
    pytest.param(atlas.PRODUCT_DOCS, "organization", id="nonprofit"),
    pytest.param(schools.PRODUCT_DOCS, "school", id="schools"),
])
def test_price_rule_survives_in_every_campaign(docs, audience):
    # Regression: this rule lived in each campaign's "What to avoid" block, and was lost
    # when those blocks were replaced by the shared standard. It cannot move into the
    # standard — the standard is campaign-agnostic and this rule names a price — so it
    # has to be asserted per campaign instead.
    assert "NEVER put the price in a first cold email" in docs
