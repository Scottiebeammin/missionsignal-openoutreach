from dataclasses import dataclass

from openoutreach.core.models import Project
from openoutreach.signals.models import InterestSignup, PilotProfile


@dataclass(frozen=True)
class PilotChecklistItem:
    label: str
    complete: bool


@dataclass(frozen=True)
class PilotContext:
    profile: PilotProfile
    current_stage: str
    next_step: str
    progress_percentage: int
    checklist: tuple[PilotChecklistItem, ...]
    snapshot_ready: bool


LIFECYCLE_PROGRESS = {
    PilotProfile.LifecycleStatus.WAITLIST: 10,
    PilotProfile.LifecycleStatus.QUALIFIED: 20,
    PilotProfile.LifecycleStatus.INVITED: 30,
    PilotProfile.LifecycleStatus.QUESTIONNAIRE_SENT: 40,
    PilotProfile.LifecycleStatus.QUESTIONNAIRE_COMPLETED: 50,
    PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS: 65,
    PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED: 75,
    PilotProfile.LifecycleStatus.WALKTHROUGH_SCHEDULED: 85,
    PilotProfile.LifecycleStatus.ACTIVE_PILOT: 92,
    PilotProfile.LifecycleStatus.PILOT_COMPLETE: 100,
}

NEXT_STEPS = {
    PilotProfile.LifecycleStatus.WAITLIST: "Review the signup and qualify fit for the pilot.",
    PilotProfile.LifecycleStatus.QUALIFIED: "Send the Founding Atlas Partner invitation.",
    PilotProfile.LifecycleStatus.INVITED: "Send discovery intake.",
    PilotProfile.LifecycleStatus.QUESTIONNAIRE_SENT: "Complete discovery intake.",
    PilotProfile.LifecycleStatus.QUESTIONNAIRE_COMPLETED: "Review intake and begin the Opportunity Web Snapshot.",
    PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS: "Schedule the founder walkthrough.",
    PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED: "Review the Snapshot and schedule the walkthrough.",
    PilotProfile.LifecycleStatus.WALKTHROUGH_SCHEDULED: "Attend the founder walkthrough.",
    PilotProfile.LifecycleStatus.ACTIVE_PILOT: "Start the 30-day action plan and track feedback.",
    PilotProfile.LifecycleStatus.PILOT_COMPLETE: "Review pilot feedback and decide the next relationship step.",
}


def create_pilot_profile_from_signup(signup: InterestSignup) -> PilotProfile:
    profile, _created = PilotProfile.objects.get_or_create(
        signup=signup,
        defaults={
            "organization_name": signup.organization,
            "contact_name": signup.name,
            "email": signup.email,
            "website": signup.website,
            "lifecycle_status": PilotProfile.LifecycleStatus.WAITLIST,
        },
    )
    return profile


def get_or_create_project_pilot_profile(project: Project) -> PilotProfile:
    profile, _created = PilotProfile.objects.get_or_create(
        project=project,
        defaults={
            "organization_name": project.organization.name,
            "contact_name": "",
            "email": "",
            "website": project.organization.website,
            "mission": project.organization.mission,
            "location": ", ".join(
                part for part in [project.organization.city, project.organization.state] if part
            ),
            "annual_budget_range": project.organization.budget_range,
            "primary_programs": project.programs,
            "communities_served": ", ".join(project.organization.beneficiaries),
            "geographic_reach": project.organization.service_area_notes,
            "current_revenue_sources": ", ".join(project.organization.current_funding_sources),
            "key_partners": ", ".join(project.organization.existing_partnerships),
            "desired_outcomes": ", ".join(project.organization.outcomes_and_impact),
            "lifecycle_status": PilotProfile.LifecycleStatus.QUALIFIED,
        },
    )
    return profile


def build_pilot_context(profile: PilotProfile) -> PilotContext:
    has_questionnaire = bool(
        profile.mission
        and profile.primary_programs
        and profile.communities_served
        and profile.top_goals
    )
    feedback_submitted = hasattr(profile, "feedback")
    checklist = (
        PilotChecklistItem("Complete Organization Profile", bool(profile.organization_name and profile.website)),
        PilotChecklistItem("Complete Discovery Questionnaire", has_questionnaire),
        PilotChecklistItem(
            "Upload Supporting Documents",
            any(
                [
                    profile.strategic_plan,
                    profile.annual_report,
                    profile.grant_materials,
                    profile.program_information,
                    profile.other_documents,
                    profile.document_notes,
                ]
            ),
        ),
        PilotChecklistItem(
            "Snapshot In Progress",
            profile.snapshot_status
            in {
                PilotProfile.SnapshotStatus.BUILDING_OPPORTUNITY_WEB,
                PilotProfile.SnapshotStatus.BUILDING_SNAPSHOT,
                PilotProfile.SnapshotStatus.INTERNAL_REVIEW,
                PilotProfile.SnapshotStatus.READY_FOR_DELIVERY,
                PilotProfile.SnapshotStatus.DELIVERED,
            },
        ),
        PilotChecklistItem("Snapshot Delivered", profile.snapshot_status == PilotProfile.SnapshotStatus.DELIVERED),
        PilotChecklistItem(
            "Founder Walkthrough Scheduled",
            profile.walkthrough_status
            in {PilotProfile.WalkthroughStatus.SCHEDULED, PilotProfile.WalkthroughStatus.COMPLETED},
        ),
        PilotChecklistItem("30-Day Action Plan Started", profile.action_plan_started),
        PilotChecklistItem("Pilot Feedback Submitted", feedback_submitted),
    )
    progress = max(
        LIFECYCLE_PROGRESS.get(profile.lifecycle_status, 10),
        round((sum(1 for item in checklist if item.complete) / len(checklist)) * 100),
    )
    return PilotContext(
        profile=profile,
        current_stage=profile.get_lifecycle_status_display(),
        next_step=NEXT_STEPS.get(profile.lifecycle_status, "Review pilot status."),
        progress_percentage=min(progress, 100),
        checklist=checklist,
        snapshot_ready=profile.snapshot_status == PilotProfile.SnapshotStatus.DELIVERED,
    )
