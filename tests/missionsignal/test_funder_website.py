"""Funder website enrichment: every funder gets an actionable link — its real
website if we have one, else a web search for the name (never a fabricated URL)."""
import pytest

from openoutreach.funding.models import Funder

pytestmark = pytest.mark.django_db


def test_real_website_is_used():
    f = Funder.objects.create(name="Batchelor Foundation", website="https://batchelorfoundation.org")
    link = f.website_or_search()
    assert link == {"url": "https://batchelorfoundation.org", "search": False}


def test_falls_back_to_web_search_when_no_website():
    f = Funder.objects.create(name="Lois M. Collier Charitable Trust", website="")
    link = f.website_or_search()
    assert link["search"] is True
    assert "google.com/search" in link["url"]
    assert "Collier" in link["url"]


def test_placeholder_website_is_ignored():
    f = Funder.objects.create(name="Demo Fund", website="https://demo.example.org")
    link = f.website_or_search()
    assert link["search"] is True                 # fake site → search instead
