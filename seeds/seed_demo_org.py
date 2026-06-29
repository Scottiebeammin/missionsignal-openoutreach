"""
Demo org seed: Westside Youth Arts Collective

Creates a realistic fictional nonprofit for demo video recording.
The org is tied to the local `admin` superuser account so you can
log in at http://localhost:8001 and see the full snapshot immediately.

Run from project root:
  DEBUG=true python seeds/seed_demo_org.py

To reset (delete and re-seed):
  DEBUG=true python seeds/seed_demo_org.py --reset
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openoutreach.settings")

import django
django.setup()

import argparse
from django.contrib.auth import get_user_model
from openoutreach.signals.services import create_organization_intake
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.core.models import Project, Organization

ORG_NAME = "Westside Youth Arts Collective"

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete existing demo org before seeding")
args = parser.parse_args()

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("ERROR: No superuser found. Create one first: python manage.py createsuperuser")
    sys.exit(1)

# Reset if requested
if args.reset:
    deleted = Organization.objects.filter(name=ORG_NAME).delete()
    print(f"Reset: deleted {deleted[0]} record(s)")

# Check if already seeded
if Project.objects.filter(organization__name=ORG_NAME).exists():
    project = Project.objects.get(organization__name=ORG_NAME)
    print(f"Demo org already exists: Project pk={project.pk}")
    print(f"  Snapshot: http://localhost:8001/projects/{project.pk}/snapshot/")
    print(f"  Public:   http://localhost:8001/s/{project.share_token}/")
    print("Run with --reset to delete and re-seed.")
    sys.exit(0)

print(f"Seeding demo org: {ORG_NAME}...")

project = create_organization_intake(
    user=user,
    contact_name="Destiny Owens",
    contact_position="Executive Director",
    contact_email="dowens@westsideyoutharts.org",
    organization_name=ORG_NAME,
    website="https://westsideyoutharts.org",
    mission=(
        "Westside Youth Arts Collective uses music, visual arts, and creative job training "
        "to support youth of color in Chicago's West Side in building futures on their own terms. "
        "We believe artistic expression and economic opportunity are inseparable."
    ),
    programs=(
        "Music Production Lab — 16-week program teaching beat-making, audio engineering, and "
        "music business fundamentals to youth ages 14–22. 40 participants per cohort, 3 cohorts/year. "
        "72% of graduates report new income from music within 6 months.\n\n"
        "Visual Arts & Design Track — after-school program for middle and high schoolers focused on "
        "graphic design, mural arts, and portfolio development. Partners with Chicago Public Schools "
        "in 5 West Side schools. 120 youth served annually.\n\n"
        "Creative Careers Apprenticeship — paid 6-month apprenticeship placing young adults (18–24) "
        "in creative industry jobs: design studios, recording studios, marketing agencies. "
        "18 apprentices per cohort. 80% placed in full-time or freelance work post-program.\n\n"
        "Summer Arts Intensive — 8-week summer program combining all three tracks with field trips, "
        "guest artist workshops, and a public showcase. 200 youth served annually."
    ),
    organization_type="nonprofit",
    city="Chicago",
    county="Cook County",
    state="IL",
    service_area_notes=(
        "Primarily serves Austin, North Lawndale, East Garfield Park, and West Garfield Park "
        "neighborhoods on Chicago's West Side. Programs are free and held in community spaces, "
        "schools, and our main facility at 4200 W. Madison St."
    ),
    outcomes_and_impact=[
        "480 youth served annually across all programs",
        "72% of Music Lab graduates earn income from music within 6 months",
        "80% of Creative Careers apprentices placed in full-time or freelance work",
        "120 youth enrolled in after-school Visual Arts program across 5 CPS schools",
        "Annual public showcase draws 600+ community members",
        "100% of programs offered free of charge to participants",
    ],
    budget_range="$250K - $1M",
    current_funding_sources=[
        "Chicago Community Trust (general operating, $75K/yr)",
        "Illinois Arts Council Agency (arts programming, $20K/yr)",
        "Individual donors (18% of budget)",
        "Program fees from partner schools (10% of budget)",
    ],
    existing_partnerships=[
        "Chicago Public Schools — 5 West Side partner schools",
        "Columbia College Chicago — mentorship and equipment access",
        "Sunshine Gospel Ministries — shared facility space",
        "WBEZ Chicago — media production mentorship",
    ],
    focus_area_selections=[
        "Youth Development",
        "Arts & Culture",
        "Workforce Development",
        "Education",
        "Economic Mobility",
    ],
    beneficiary_selections=[
        "youth",
        "communities of color",
        "low-income residents",
        "job seekers",
    ],
    intake_notes=(
        "We're trying to grow from $600K to $1.2M over the next two years to open a second location "
        "in South Lawndale. We've never applied for federal grants before and don't know where to start. "
        "We also need a workforce board partnership to unlock state workforce funding — we've been told "
        "we qualify but don't know how to navigate that relationship."
    ),
)

# Run analysis so snapshot has real data
print("Running analysis...")
try:
    analyze_project(project, mode="deterministic")
    print("Analysis complete.")
except Exception as e:
    print(f"Analysis warning (non-fatal): {e}")

# Link admin user if not already linked
if not project.users.filter(pk=user.pk).exists():
    project.users.add(user)

print()
print(f"✓ Demo org created: {ORG_NAME}")
print(f"  Project pk:  {project.pk}")
print(f"  Share token: {project.share_token}")
print()
print(f"  Snapshot:    http://localhost:8001/projects/{project.pk}/snapshot/")
print(f"  Public URL:  http://localhost:8001/s/{project.share_token}/")
print(f"  Dashboard:   http://localhost:8001/projects/{project.pk}/dashboard/")
print(f"  Web:         http://localhost:8001/projects/{project.pk}/web/")
print()
print("Log in as:", user.username)
print("Then visit the Snapshot URL above to start recording.")
