from dataclasses import dataclass

from openoutreach.signals.models import Celebration


@dataclass(frozen=True)
class CelebrationMetrics:
    celebrations_shared: int
    opportunities_awarded: int
    partnerships_formed: int
    impact_stories_shared: int


@dataclass(frozen=True)
class CelebrationOverview:
    recent_celebrations: list[Celebration]
    featured_celebrations: list[Celebration]
    metrics: CelebrationMetrics


def build_celebration_overview(project) -> CelebrationOverview:
    celebrations = list(project.celebrations.all())
    return CelebrationOverview(
        recent_celebrations=celebrations[:12],
        featured_celebrations=[
            celebration
            for celebration in celebrations
            if celebration.celebration_type in {
                Celebration.CelebrationType.OPPORTUNITY_AWARDED,
                Celebration.CelebrationType.IMPACT_MILESTONE,
                Celebration.CelebrationType.SUCCESS_STORY,
                Celebration.CelebrationType.COMMUNITY_ACHIEVEMENT,
            }
        ][:4],
        metrics=CelebrationMetrics(
            celebrations_shared=len(celebrations),
            opportunities_awarded=sum(
                1 for celebration in celebrations
                if celebration.celebration_type == Celebration.CelebrationType.OPPORTUNITY_AWARDED
            ),
            partnerships_formed=sum(
                1 for celebration in celebrations
                if celebration.celebration_type == Celebration.CelebrationType.PARTNERSHIP_FORMED
            ),
            impact_stories_shared=sum(
                1 for celebration in celebrations
                if celebration.celebration_type in {
                    Celebration.CelebrationType.IMPACT_MILESTONE,
                    Celebration.CelebrationType.SUCCESS_STORY,
                    Celebration.CelebrationType.COMMUNITY_ACHIEVEMENT,
                }
            ),
        ),
    )
