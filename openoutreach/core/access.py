"""
Account verification gate.

Anyone may create an account (open sign-up), but the portal is only reachable
for VERIFIED users:
  - staff,
  - members of any project (invited via a signed invite link, or onboarded), or
  - members of the "Founding Partners" group (added by the Stripe webhook the
    moment their founding-seat payment lands).

Everyone else is routed to the activation paywall (/activate/).
"""

import os

from django.contrib.auth.models import Group

FOUNDING_PARTNERS_GROUP = "Founding Partners"
# Buyers of the $50/mo Snapshot tier land here at webhook time (before a project
# exists), mirroring "Founding Partners". Their project is stamped tier=snapshot at intake.
SNAPSHOT_PARTNERS_GROUP = "Snapshot Members"

# The founding-seat Stripe payment link (same one the landing page uses).
STRIPE_FOUNDING_SEAT_URL = "https://buy.stripe.com/3cI28q4PM4Xw3cPfnzbV601"
# The $50/mo Snapshot payment link — set once created in the Stripe dashboard.
STRIPE_SNAPSHOT_URL = os.environ.get("STRIPE_SNAPSHOT_URL", "")


def founding_partners_group() -> Group:
    group, _ = Group.objects.get_or_create(name=FOUNDING_PARTNERS_GROUP)
    return group


def snapshot_partners_group() -> Group:
    group, _ = Group.objects.get_or_create(name=SNAPSHOT_PARTNERS_GROUP)
    return group


def project_has_live_access(project) -> bool:
    """Full-seat projects get the interactive workspace; Snapshot-tier projects are read-only.

    Gate interactive features on THIS (the workspace's tier), never on the user's
    group — a full org's invited teammates are plain members with no group.
    """
    from openoutreach.core.models import Project
    return getattr(project, "tier", Project.Tier.FULL) == Project.Tier.FULL


def user_is_verified(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if user.groups.filter(name=FOUNDING_PARTNERS_GROUP).exists():
        return True
    return user.missionsignal_projects.exists()


def user_is_project_admin(user, project) -> bool:
    """Seat authority: staff, or the member flagged is_admin on this project.

    The first seat on a project is the admin (intake owner, or the first
    invite accepted); admins can edit profile settings like areas of support.
    """
    if user.is_staff:
        return True
    from openoutreach.core.models import OrganizationMember
    return OrganizationMember.objects.filter(project=project, user=user, is_admin=True).exists()
