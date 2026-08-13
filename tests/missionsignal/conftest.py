"""Deterministic environment for the missionsignal (Atlas) test suite.

The send path refuses to run without a CAN-SPAM mailing address — correct in
production, but as a shell-environment dependency it made the whole suite's
result depend on what happened to be exported (`OUTREACH_MAILING_ADDRESS`
missing = 32 spurious failures). Tests must not inherit safety-critical config
from the developer's shell: this fixture pins the module constant for every
test, and a test that needs the *missing*-address behavior monkeypatches it
back to "" explicitly. Production is untouched — the real env var remains
required, and its absence still fails closed at send time.
"""
from __future__ import annotations

import pytest

TEST_MAILING_ADDRESS = "7901 4th St N STE 300, St. Petersburg, FL 33702"


@pytest.fixture(autouse=True)
def _mailing_address(monkeypatch):
    from openoutreach.signals import outreach

    monkeypatch.setattr(outreach, "OUTREACH_MAILING_ADDRESS", TEST_MAILING_ADDRESS)
