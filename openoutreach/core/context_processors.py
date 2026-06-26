from openoutreach.core.models import OrganizationMember, Project


def onboarding(request):
    if not request.user.is_authenticated:
        return {}
    project = Project.objects.filter(users=request.user).first()
    if not project:
        return {}
    member = OrganizationMember.objects.filter(user=request.user, project=project).first()
    if not member:
        return {}
    return {
        "onboarding_member": member,
        "onboarding_steps": member.onboarding_progress(),
        "onboarding_complete": member.onboarding_complete,
        "show_tour": not member.has_toured,
    }
