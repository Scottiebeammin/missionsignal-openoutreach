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

from django.contrib.auth.models import Group

FOUNDING_PARTNERS_GROUP = "Founding Partners"

# The founding-seat Stripe payment link (same one the landing page uses).
STRIPE_FOUNDING_SEAT_URL = "https://buy.stripe.com/3cI28q4PM4Xw3cPfnzbV601"


def founding_partners_group() -> Group:
    group, _ = Group.objects.get_or_create(name=FOUNDING_PARTNERS_GROUP)
    return group


def user_is_verified(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if user.groups.filter(name=FOUNDING_PARTNERS_GROUP).exists():
        return True
    return user.missionsignal_projects.exists()
