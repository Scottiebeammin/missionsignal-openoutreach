import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from openoutreach.funding.models import Opportunity, SourceOrganization
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.discovery import build_discovery_overview


pytestmark = pytest.mark.django_db


@pytest.fixture
def discovery_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_project_member_can_view_discovery_dashboard(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Discovery Engine V2" in content
    assert "Opportunity Inventory" in content
    assert "Total Opportunities" in content
    assert "Active" in content
    assert "Monitoring" in content
    assert "Applied" in content
    assert "Won" in content


def test_non_member_cannot_view_discovery_dashboard(client, discovery_project):
    project, _ = discovery_project
    outsider = get_user_model().objects.create_user(username="discovery-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_discovery_inventory_and_readiness_render(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Opportunity Inventory Summary" in content
    assert "Command Center Filters" in content
    assert "Search Opportunities" in content
    assert "More Filters" in content
    assert "Match Level" in content
    assert "Top Source Organizations" in content
    assert "Opportunity Status Breakdown" in content
    assert "Filters" in content
    assert "Focus Area" in content
    assert "Top Categories" in content
    assert "More categories" in content
    assert "Grants" in content
    assert "Government" in content
    assert "Resources" in content
    assert "Partnerships" in content
    assert "Digital Equity Grant" in content
    assert "Workforce Development Grant" in content
    assert "Youth Technology Initiative" in content
    assert "Community Partnership Program" in content
    assert "Capacity Building Resource Program" in content
    assert "Youth Career Exploration Sponsorship" in content
    assert "Match Score" in content
    assert "View Details" in content
    assert "Source Organization" in content
    assert "Current Lifecycle Status" in content
    assert "Status History" in content
    assert "Last Updated" in content
    assert "Discovered" in content
    assert "Why It Matches" in content
    assert "Missing Factors" in content
    assert "Improvement Opportunities" in content
    assert "Focus Areas" in content
    assert "Eligibility Notes" in content
    assert "Internal Notes" in content
    assert "Recommended Actions" in content
    assert "Deadline:" in content
    assert "High" in content
    assert "Strong Match" in content or "Excellent Match" in content


def test_discovery_dashboard_renders_expanded_focus_categories(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Veterans" in content
    assert "Mental Health" in content
    assert "LGBTQ+" in content
    assert "Disability" in content
    assert "Food Security" in content
    assert "Reentry / Justice-Involved" in content
    assert "Senior Services" in content
    assert "Immigrant / Refugee Support" in content
    assert "Environmental Justice" in content
    assert "Rural Communities" in content


def test_discovery_pipeline_renders(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Opportunity Pipeline" in content
    assert "High Priority" in content
    assert "Medium Priority" in content
    assert "Low Priority" in content


def test_discovery_demo_records_are_deterministic_and_varied(discovery_project):
    project, _user = discovery_project
    first = build_discovery_overview(project, project.funding_criteria)
    second = build_discovery_overview(project, project.funding_criteria)
    scores = [
        item.match.score
        for group in first.groups
        for item in group.opportunities
    ]

    assert first.total_opportunities >= 29
    assert first.active_opportunities >= 8
    assert first.monitoring_opportunities >= 3
    assert first.high_priority_opportunities >= 6
    assert first.best_opportunity_category == second.best_opportunity_category
    assert [item.opportunity.name for item in first.top_opportunities] == [
        item.opportunity.name for item in second.top_opportunities
    ]
    assert Opportunity.objects.filter(name="Digital Equity Grant").count() == 1
    assert SourceOrganization.objects.filter(name="Cuyahoga Community Foundation").count() == 1
    assert max(scores) >= 90
    assert min(scores) < 60
    assert len(set(scores)) >= 4
    category_labels = {category.label for category in first.focus_categories}
    assert "Veterans" in category_labels
    assert "Mental Health" in category_labels
    assert "Environmental Justice" in category_labels


def test_ecosystem_dashboard_includes_discovery_summary(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Discovery Health" in content
    assert "Total Opportunities" in content
    assert "Active Opportunities" in content
    assert "Monitoring Opportunities" in content
    assert "High Priority Opportunities" in content
    assert "Top Source Organization" in content
    assert "Open Discovery Engine" in content
    assert reverse("project-discovery", kwargs={"pk": project.pk}) in content


def test_discovery_navigation_links_render(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content


def test_opportunity_csv_import_workflow(tmp_path):
    csv_path = tmp_path / "opportunities.csv"
    csv_path.write_text(
        "\n".join([
            "name,opportunity_type,geography,status,source organization,deadline,notes,focus areas,beneficiaries,priority",
            (
                "Imported Digital Skills Grant,Grant,Cleveland;Ohio,Active,"
                "Imported Foundation,2026-08-01,Imported note,"
                "digital equity;workforce development,youth;job seekers,High"
            ),
            (
                "Imported Housing Partnership,Partnership,Cuyahoga County,Monitoring,"
                "Imported Nonprofit,09/15/2026,Partnership note,"
                "housing;community development,families,Low"
            ),
        ]),
        encoding="utf-8",
    )

    call_command("import_opportunities_csv", str(csv_path))

    grant = Opportunity.objects.get(name="Imported Digital Skills Grant")
    partnership = Opportunity.objects.get(name="Imported Housing Partnership")
    assert grant.source_organization.name == "Imported Foundation"
    assert grant.status == Opportunity.Status.ACTIVE
    assert grant.priority_level == Opportunity.PriorityLevel.HIGH
    assert grant.deadline.isoformat() == "2026-08-01"
    assert grant.focus_areas == ["digital equity", "workforce development"]
    assert grant.beneficiaries == ["youth", "job seekers"]
    assert partnership.status == Opportunity.Status.MONITORING
    assert partnership.priority_level == Opportunity.PriorityLevel.LOW
