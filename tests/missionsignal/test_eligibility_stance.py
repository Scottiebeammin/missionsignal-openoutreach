"""Grants.gov applicant-type codes can't answer "can this nonprofit apply" — NSF
tags nearly everything type 25, "Others (see text field)". The answer is in the
eligibility prose, and these lock in reading it correctly.

Two failure modes matter, and they pull in opposite directions: reading only the
first track of a multi-track program (marks LSAMP closed when its NETWORKS track
admits nonprofits), and reading the whole document (lets a "Who May Serve as PI"
mention make a genuinely restricted program look open). The answer lives in the
"Who May Submit Proposals" block, all of it and nothing after it.
"""
import pytest

from openoutreach.funding.relevance import (
    ELIGIBILITY_OPEN,
    ELIGIBILITY_RESTRICTED,
    ELIGIBILITY_UNKNOWN,
    eligibility_rank,
    eligibility_stance,
)


class FakeOpportunity:
    def __init__(self, eligibility_notes=""):
        self.eligibility_notes = eligibility_notes


# Verbatim shape of NSF's Advanced Technological Education notice.
ATE = (
    "*Who May Submit Proposals: Proposals may only be submitted by the following: "
    "-For-profit organizations: U.S.-based commercial organizations, including small "
    "businesses, with strong capabilities in scientific or engineering research or "
    "education and a passion for innovation. -Non-profit, non-academic organizations: "
    "Independent museums, observatories, research laboratories, professional societies "
    "and similar organizations located in the U.S. that are directly associated with "
    "educational or research activities. -State and Local Governments "
    "-Institutions of Higher Education (IHEs): Two- and four-year IHEs accredited in, "
    "and having a campus located in the US, acting on behalf of their faculty members."
)

# Real shape of NSF's LSAMP notice: a MULTI-TRACK program. Its first three tracks
# (ADG, SPIO, SPRA) are IHE-only, and a reader who stops there concludes the whole
# program is closed to nonprofits — which is what a human did before this test
# existed. The NETWORKS track further down admits non-profit, non-academic
# organizations, so the correct answer for the program is "open".
LSAMP_MULTITRACK = (
    "*Who May Submit Proposals: Proposals may only be submitted by the following: "
    "- Alliance Development Grants (ADG) &lt;ul&gt; &lt;li&gt;Institutions of Higher "
    "Education (IHEs) - Two-and-four-year IHEs (including community colleges) accredited "
    "in and having a campus located in the US, acting on behalf of their faculty "
    "members.&lt;/li&gt; &lt;/ul&gt; Alliances: &lt;li&gt;STEM Pathways Implementation-Only "
    "(SPIO): Institutions of Higher Education (IHEs)&lt;/li&gt; "
    "Networking Incentives and Engagement (NETWORKS)&lt;br /&gt; &lt;ul&gt; "
    "&lt;li&gt;Institutions of Higher Education (IHEs)&lt;/li&gt; "
    "&lt;li&gt;Non-profit, non-academic organizations: Independent museums, observatories, "
    "research laboratories, professional societies and similar organizations located in "
    "the U.S.&lt;/li&gt;&lt;/ul&gt;"
)


def test_ate_is_open_to_nonprofits():
    assert eligibility_stance(FakeOpportunity(ATE)) == ELIGIBILITY_OPEN


def test_a_multitrack_program_is_open_if_any_track_admits_nonprofits():
    """Regression on a real mistake: LSAMP's first three tracks are IHE-only, and
    stopping there marks the program closed. Its NETWORKS track admits non-profit,
    non-academic organizations, so the program is open — on that track."""
    assert eligibility_stance(FakeOpportunity(LSAMP_MULTITRACK)) == ELIGIBILITY_OPEN
    assert eligibility_rank(FakeOpportunity(LSAMP_MULTITRACK)) == 0


def test_a_later_section_cannot_leak_categories_into_the_answer():
    """NSF delimits sections with "*". A nonprofit mention under "Who May Serve as PI"
    must not make a genuinely restricted program look open."""
    crest_then_pi = (
        "*Who May Submit Proposals: Eligible institutions are MSIs that offer graduate "
        "degrees in NSF STEM areas. "
        "*Who May Serve as PI: staff at any non-profit collaborator."
    )
    assert eligibility_stance(FakeOpportunity(crest_then_pi)) == ELIGIBILITY_RESTRICTED


def test_crest_style_msi_restriction_is_caught():
    notice = (
        "*Who May Submit Proposals: Eligible institutions are MSIs that offer graduate "
        "degrees in NSF STEM areas and have enrollments of 50% or more students who are "
        "members of minority groups underrepresented among those holding doctorates."
    )
    assert eligibility_stance(FakeOpportunity(notice)) == ELIGIBILITY_RESTRICTED


@pytest.mark.parametrize("notes", ["", "   ", None])
def test_missing_text_is_unknown_never_restricted(notes):
    assert eligibility_stance(FakeOpportunity(notes)) == ELIGIBILITY_UNKNOWN


def test_prose_without_a_who_may_submit_header_still_reads_categories():
    notice = "Eligibility: applications are accepted from nonprofit organizations and units of local government."
    assert eligibility_stance(FakeOpportunity(notice)) == ELIGIBILITY_OPEN


def test_unstated_eligibility_is_not_treated_as_a_restriction():
    """Hiding a grant the client could have won is worse than showing one they
    have to read twice, so silence must never rank as restricted."""
    notice = "Applicants must meet all requirements discussed in this NOFO."
    assert eligibility_stance(FakeOpportunity(notice)) == ELIGIBILITY_UNKNOWN
    assert eligibility_rank(FakeOpportunity(notice)) == 0


def test_only_restricted_is_demoted():
    assert eligibility_rank(FakeOpportunity(ATE)) == 0
    assert eligibility_rank(FakeOpportunity("")) == 0
    assert eligibility_rank(FakeOpportunity(LSAMP_MULTITRACK)) == 0


def test_html_entities_are_decoded_before_matching():
    notice = "*Who May Submit Proposals: &lt;ul&gt;&lt;li&gt;Non-profit organizations&lt;/li&gt;&lt;/ul&gt;"
    assert eligibility_stance(FakeOpportunity(notice)) == ELIGIBILITY_OPEN
