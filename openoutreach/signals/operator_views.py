import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _operator_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


@_operator_required
def operator_dashboard(request):
    from openoutreach.core.models import Project
    from openoutreach.funding.models import Funder, Opportunity, PartnerOrganization

    # Find the InterestSignup model - try both possible locations
    try:
        from openoutreach.signals.models import InterestSignup
        recent_signups = InterestSignup.objects.order_by("-created_at")[:5]
        total_signups = InterestSignup.objects.count()
    except (ImportError, Exception):
        recent_signups = []
        total_signups = 0

    from django.db.models import Count
    projects = (
        Project.objects.select_related("organization")
        .annotate(opp_count=Count("opportunities", distinct=True))
        .order_by("-created_at")
    )
    total_projects = projects.count()

    # Projects with no opportunities (need research)
    needs_research = projects.filter(opp_count=0)

    # Sales-pipeline summary card (segmented command center)
    from django.utils import timezone
    from openoutreach.signals.models import SalesLead
    today = timezone.localdate()
    pipeline_summary = {
        "total": SalesLead.objects.count(),
        "warm": SalesLead.objects.filter(list_segment=SalesLead.Segment.WARM).count(),
        "cold_florida": SalesLead.objects.filter(
            list_segment=SalesLead.Segment.COLD_FLORIDA_CRM
        ).count(),
        "call_list": SalesLead.objects.filter(
            list_segment=SalesLead.Segment.COLD_CALL_LIST
        ).count(),
        "due_today": SalesLead.objects.filter(next_follow_up__lte=today).count(),
        "closed": SalesLead.objects.filter(status=SalesLead.Status.CLOSED).count(),
    }
    # Outreach cockpit status: emailable leads still to send vs already sent.
    outreach_summary = {
        "to_send": SalesLead.objects.filter(email_status="not_sent").exclude(email="").count(),
        "sent": SalesLead.objects.filter(email_status="sent").count(),
    }

    # Orgs with any member seen in the last 7 days (ClientActivityTracker stamps).
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    active_orgs_week = (
        Project.objects.filter(members__last_seen_at__gte=week_ago).distinct().count()
    )

    ctx = {
        "pipeline_summary": pipeline_summary,
        "outreach_summary": outreach_summary,
        "total_projects": total_projects,
        "active_orgs_week": active_orgs_week,
        "total_signups": total_signups,
        "total_funders": Funder.objects.filter(active=True).count(),
        "total_opportunities": Opportunity.objects.count(),
        "recent_signups": recent_signups,
        "needs_research": needs_research[:5],
        "recent_projects": projects[:5],
    }
    return render(request, "signals/operator/dashboard.html", ctx)


@_operator_required
def operator_organizations(request):
    from openoutreach.core.models import OrganizationMember, Project
    from django.db.models import Count, Max, OuterRef, Subquery, Sum

    # Member activity via subqueries — joining members alongside the opportunity
    # Count would cross-multiply rows and inflate the Sum.
    member_activity = (
        OrganizationMember.objects.filter(project=OuterRef("pk"))
        .values("project")
        .annotate(last_seen=Max("last_seen_at"), views=Sum("page_views"))
    )
    projects = (
        Project.objects.select_related("organization")
        .annotate(
            opp_count=Count("opportunities", distinct=True),
            last_seen=Subquery(member_activity.values("last_seen")[:1]),
            total_page_views=Subquery(member_activity.values("views")[:1]),
        )
        .order_by("-created_at")
    )

    ctx = {"projects": projects}
    return render(request, "signals/operator/organizations.html", ctx)


@_operator_required
def operator_org_detail(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.funding.models import Funder, Opportunity, PartnerOrganization, GovernmentEntity, ResourceProvider
    from django.db.models import Count

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)

    opportunities = Opportunity.objects.filter(project=project).order_by("-created_at")
    opp_by_type = {}
    for opp in opportunities:
        t = opp.get_opportunity_type_display()
        opp_by_type[t] = opp_by_type.get(t, 0) + 1

    # For the displayed "Top Opportunities", show relevant, US-eligible ones (matches
    # what the client sees) — not raw off-topic/foreign grants.
    from openoutreach.funding.relevance import org_keywords, opportunity_relevance, is_off_geography, is_research_grant
    _kw = org_keywords(project.organization)
    top_opportunities = [
        o for o in opportunities
        if not is_off_geography(o, project.organization)
        and not is_research_grant(o)
        and opportunity_relevance(o, _kw) > 0
    ][:10] or list(opportunities[:10])

    try:
        from openoutreach.signals.models import OrganizationAnalysisRun
        last_analysis = OrganizationAnalysisRun.objects.filter(project=project).order_by("-created_at").first()
    except Exception:
        last_analysis = None

    ctx = {
        "project": project,
        "org": project.organization,
        "opportunities": top_opportunities,
        "opp_by_type": opp_by_type,
        "opp_count": opportunities.count(),
        "last_analysis": last_analysis,
    }
    return render(request, "signals/operator/org_detail.html", ctx)


@_operator_required
@require_POST
def operator_run_research(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.signals.research import research_project

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)
    try:
        counts = research_project(project)
        parts = [f"{v} {k}" for k, v in counts.items() if v]
        messages.success(request, f"Research complete for {project.organization.name}: {', '.join(parts)}")
    except Exception as e:
        messages.error(request, f"Research failed: {e}")
    return redirect("operator-org-detail", pk=pk)


@_operator_required
@require_POST
def operator_run_analysis(request, pk):
    from openoutreach.core.models import Project
    from openoutreach.signals.analysis_service import analyze_project

    project = get_object_or_404(Project.objects.select_related("organization"), pk=pk)
    try:
        analyze_project(project)
        messages.success(request, f"Analysis complete for {project.organization.name}.")
    except Exception as e:
        messages.error(request, f"Analysis failed: {e}")
    return redirect("operator-org-detail", pk=pk)


@_operator_required
@_operator_required
@require_POST
def operator_waitlist_status(request, pk):
    from openoutreach.signals.models import InterestSignup
    signup = get_object_or_404(InterestSignup, pk=pk)
    new_status = request.POST.get("status", "").strip()
    if new_status in InterestSignup.Status.values:
        signup.status = new_status
        signup.save(update_fields=["status"])
        messages.success(request, f"Updated {signup.name} → {signup.get_status_display()}")
    else:
        messages.error(request, f"Invalid status: {new_status}")
    return redirect("operator-waitlist")


@_operator_required
def operator_funders(request):
    from openoutreach.funding.models import Funder
    status_filter = request.GET.get("status", "")
    qs = Funder.objects.order_by("verification_status", "name")
    if status_filter:
        qs = qs.filter(verification_status=status_filter)

    # Normalize geography to list for consistent template rendering
    funders = list(qs)
    for f in funders:
        if isinstance(f.geography, str):
            f.geography = [f.geography] if f.geography else []

    from django.db.models import Count
    status_counts = {
        row["verification_status"]: row["count"]
        for row in Funder.objects.values("verification_status").annotate(count=Count("id"))
    }
    ctx = {
        "funders": funders,
        "status_filter": status_filter,
        "status_counts": status_counts,
        "total": Funder.objects.count(),
    }
    return render(request, "signals/operator/funders.html", ctx)


@_operator_required
@require_POST
def operator_funder_verify(request, pk):
    from openoutreach.funding.models import Funder
    from django.utils import timezone
    funder = get_object_or_404(Funder, pk=pk)
    new_status = request.POST.get("verification_status", "").strip()
    note = request.POST.get("note", "").strip()
    if new_status in Funder.VerificationStatus.values:
        funder.verification_status = new_status
        funder.last_reviewed_at = timezone.now()
        if note:
            funder.notes = (funder.notes + "\n\n" + note).strip() if funder.notes else note
        funder.save(update_fields=["verification_status", "last_reviewed_at", "notes"])
        messages.success(request, f"{funder.name} → {funder.get_verification_status_display()}")
    else:
        messages.error(request, f"Invalid status: {new_status}")
    next_url = request.POST.get("next", "operator-funders")
    status_param = request.POST.get("status_filter", "")
    base = redirect("operator-funders")
    if status_param:
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse("operator-funders") + f"?status={status_param}")
    return redirect("operator-funders")


@_operator_required
@require_POST
def operator_research_funder(request, pk):
    from openoutreach.funding.models import Funder
    from openoutreach.signals.research import research_funder
    import threading

    funder = get_object_or_404(Funder, pk=pk)
    status_filter = request.POST.get("status_filter", "")

    def _run():
        try:
            research_funder(funder)
        except Exception as e:
            logger.error("Funder research failed for pk=%s: %s", pk, e)

    threading.Thread(target=_run, daemon=True).start()
    messages.success(request, f"Research started for {funder.name} — refresh in a moment.")
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    url = reverse("operator-funders")
    if status_filter:
        url += f"?status={status_filter}"
    return HttpResponseRedirect(url)


@_operator_required
@require_POST
def operator_enrich_signup(request, pk):
    from openoutreach.signals.models import InterestSignup
    from openoutreach.signals.research import research_signup
    import threading

    signup = get_object_or_404(InterestSignup, pk=pk)

    def _run():
        try:
            research_signup(signup)
        except Exception as e:
            logger.error("Signup enrichment failed for pk=%s: %s", pk, e)

    threading.Thread(target=_run, daemon=True).start()
    messages.success(request, f"Enrichment started for {signup.organization or signup.email} — refresh in a moment.")
    return redirect("operator-waitlist")


@_operator_required
def operator_pipeline(request):
    from django.db.models import Case, IntegerField, Q, Value, When
    from django.utils import timezone

    from openoutreach.signals.models import SalesLead

    status_filter = request.GET.get("status", "")
    source_filter = request.GET.get("source", "")
    segment_filter = request.GET.get("segment", "")
    if segment_filter not in SalesLead.Segment.values:
        segment_filter = ""

    today = timezone.localdate()

    segment_counts = {
        seg.value: SalesLead.objects.filter(list_segment=seg).count()
        for seg in SalesLead.Segment
    }

    segment_qs = SalesLead.objects.all()
    if segment_filter:
        segment_qs = segment_qs.filter(list_segment=segment_filter)

    qs = segment_qs
    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)

    # Sort: due follow-ups first, then warmth (hot > warm > reconnect > cold),
    # then organization.
    qs = qs.annotate(
        due_rank=Case(
            When(next_follow_up__lte=today, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        warmth_rank=Case(
            When(warmth=SalesLead.Warmth.HOT, then=Value(0)),
            When(warmth=SalesLead.Warmth.WARM, then=Value(1)),
            When(warmth=SalesLead.Warmth.RECONNECT, then=Value(2)),
            When(warmth=SalesLead.Warmth.COLD, then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        ),
    ).order_by("due_rank", "warmth_rank", "organization", "name")

    # Per-status counts within the current segment (summary header cards).
    status_counts = {s.value: segment_qs.filter(status=s).count() for s in SalesLead.Status}
    due_count = segment_qs.filter(next_follow_up__lte=today).count()

    ctx = {
        "leads": qs,
        "status_filter": status_filter,
        "source_filter": source_filter,
        "segment_filter": segment_filter,
        "segment_counts": segment_counts,
        "segment_total": segment_qs.count(),
        "status_counts": status_counts,
        "due_count": due_count,
        "today": today,
        "total": SalesLead.objects.count(),
        "closed": status_counts.get("closed", 0),
        "statuses": SalesLead.Status.choices,
        "sources": SalesLead.Source.choices,
        "segments": SalesLead.Segment.choices,
    }
    return render(request, "signals/operator/pipeline.html", ctx)


@_operator_required
@require_POST
def operator_pipeline_add(request):
    from openoutreach.signals.models import SalesLead
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name is required.")
        return redirect("operator-pipeline")
    SalesLead.objects.create(
        name=name,
        organization=request.POST.get("organization", "").strip(),
        email=request.POST.get("email", "").strip(),
        phone=request.POST.get("phone", "").strip(),
        role=request.POST.get("role", "").strip(),
        linkedin_url=request.POST.get("linkedin_url", "").strip(),
        source=request.POST.get("source", SalesLead.Source.WARM),
        notes=request.POST.get("notes", "").strip(),
    )
    messages.success(request, f"Added {name} to the pipeline.")
    return redirect("operator-pipeline")


@_operator_required
@require_POST
def operator_pipeline_update(request, pk):
    from openoutreach.signals.models import SalesLead
    lead = get_object_or_404(SalesLead, pk=pk)
    new_status = request.POST.get("status", "").strip()
    note = request.POST.get("note", "").strip()
    follow_up = request.POST.get("next_follow_up", "").strip()

    update_fields = []
    if new_status in SalesLead.Status.values:
        lead.status = new_status
        update_fields.append("status")
    if note:
        from django.utils import timezone
        stamp = timezone.now().strftime("%b %-d")
        lead.notes = (f"[{stamp}] {note}\n\n" + lead.notes).strip()
        update_fields.append("notes")
    if follow_up:
        from datetime import date
        try:
            lead.next_follow_up = date.fromisoformat(follow_up)
            update_fields.append("next_follow_up")
        except ValueError:
            pass
    if update_fields:
        update_fields.append("updated_at")
        lead.save(update_fields=update_fields)
    messages.success(request, f"Updated {lead.name}.")
    return redirect("operator-pipeline")


@_operator_required
def operator_ads(request):
    """AI ad-copy generator for Anansi Atlas marketing (LinkedIn/IG/FB/X/Google)."""
    result = None
    form = {"platform": "LinkedIn", "focus": "the founding cohort offer", "angle": "", "count": "3"}
    if request.method == "POST":
        from pydantic_ai import Agent
        from openoutreach.core.llm import get_llm_model, run_agent_sync

        form = {
            "platform": request.POST.get("platform", "LinkedIn"),
            "focus": request.POST.get("focus", "").strip(),
            "angle": request.POST.get("angle", "").strip(),
            "count": request.POST.get("count", "3"),
        }
        prompt = f"""You are a performance marketer for Anansi Atlas — a nonprofit opportunity intelligence platform that maps aligned funders, partners, government pathways, and readiness gaps for nonprofit Executive Directors. Founding partner rate is $150/month, locked for life.

Write {form['count']} distinct {form['platform']} ad variations promoting: {form['focus'] or 'Anansi Atlas'}.
{f"Angle / tone: {form['angle']}" if form['angle'] else ''}

Audience: nonprofit Executive Directors and development directors who struggle to find funding aligned to their mission.
Each variation: a scroll-stopping hook (1 line), 2-3 sentences of body that name a real pain and the payoff, and a clear CTA pointing to anansiatlas.com. Match {form['platform']} length and conventions. Number each variation clearly. Use hashtags only for Instagram or X.
Return only the ad copy."""
        try:
            agent = Agent(get_llm_model(), model_settings={"temperature": 0.8, "timeout": 60})
            result = run_agent_sync(agent.run(prompt)).output.strip()
        except Exception as e:
            messages.error(request, f"Generation failed: {e}")
    return render(request, "signals/operator/ads.html", {"result": result, "form": form})


@_operator_required
@require_POST
def operator_pipeline_draft(request, pk):
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import compose_outreach_email

    lead = get_object_or_404(SalesLead, pk=pk)
    source_label = lead.get_source_display()
    tone = "warm, personal, reference shared context" if lead.source == SalesLead.Source.WARM else "professional cold outreach, concise"

    prompt = f"""Write a short sales outreach email for Anansi Atlas — a nonprofit opportunity intelligence platform ($150/month founding partner rate).

Lead details:
- Name: {lead.name}
- Organization: {lead.organization or 'unknown'}
- Role: {lead.role or 'unknown'}
- Source: {source_label}
- Notes: {lead.notes or 'none'}

Tone: {tone}
Length: 5-8 sentences max. No subject line. No sign-off needed (we'll add it).
Goal: get them on a 45-minute founder walkthrough call.
Do not mention pricing unless they asked. End with a soft CTA — "would love to show you what it looks like for [org name]" style.
Return only the email body text."""

    # Prefer the AI writer when an LLM key is configured; otherwise (or on any
    # LLM error) fall back to the deterministic template composer so the button
    # always produces a usable draft — no scary "Draft failed" for the common
    # no-LLM-key setup. The cockpit's Cold/Warm tabs use the same composer.
    try:
        from pydantic_ai import Agent
        from openoutreach.core.llm import get_llm_model, run_agent_sync
        agent = Agent(get_llm_model(), model_settings={"temperature": 0.7, "timeout": 60})
        lead.outreach_draft = run_agent_sync(agent.run(prompt)).output.strip()
        lead.save(update_fields=["outreach_draft", "updated_at"])
        messages.success(request, f"AI draft generated for {lead.name}.")
    except Exception:
        _subject, body = compose_outreach_email(lead)
        lead.outreach_draft = body
        lead.save(update_fields=["outreach_draft", "updated_at"])
        messages.success(
            request,
            f"Draft ready for {lead.name} (from the built-in template — add an LLM key in "
            f"Site Config if you want AI-written drafts).",
        )
    return redirect("operator-pipeline")


@_operator_required
@require_POST
def operator_pipeline_delete(request, pk):
    from openoutreach.signals.models import SalesLead
    lead = get_object_or_404(SalesLead, pk=pk)
    name = lead.name
    lead.delete()
    messages.success(request, f"Removed {name} from pipeline.")
    return redirect("operator-pipeline")


_OUTREACH_WARMTH = {"hot": 0, "warm": 1, "reconnect": 2, "cold": 3}
_OUTREACH_LIMIT = 20  # "top 20" per email tab by default


@_operator_required
def operator_outreach(request):
    """Outreach cockpit, three tabs: Warm (top 20 email), Cold (top 20 email),
    and a Call List (phone-only orgs with their call script). Every email send
    is a deliberate per-lead click; the call tab is a to-call worklist."""
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import draft_for

    tab = request.GET.get("tab", "warm")
    if tab not in ("warm", "cold", "call"):
        tab = "warm"
    show_all = request.GET.get("all") == "1"

    def email_leads(segment):
        leads = list(SalesLead.objects.filter(list_segment=segment, email_status="not_sent").exclude(email=""))
        leads.sort(key=lambda l: (
            0 if l.outreach_draft else 1,               # hand-written drafts first
            _OUTREACH_WARMTH.get(l.warmth, 9),
            (l.organization or "").casefold(),
        ))
        return leads

    warm_all = email_leads(SalesLead.Segment.WARM)
    cold_all = email_leads(SalesLead.Segment.COLD_FLORIDA_CRM)
    call_all = list(
        SalesLead.objects.filter(list_segment=SalesLead.Segment.COLD_CALL_LIST, email_status="not_sent")
        .order_by("organization")
    )
    counts = {"warm": len(warm_all), "cold": len(cold_all), "call": len(call_all)}

    source = {"warm": warm_all, "cold": cold_all, "call": call_all}[tab]
    total = len(source)
    shown = source if (show_all or tab == "call") else source[:_OUTREACH_LIMIT]

    cards = []
    if tab == "call":
        for lead in shown:
            cards.append({"lead": lead, "script": lead.outreach_draft or "", "phone": lead.phone})
    else:
        for lead in shown:
            subject, body = draft_for(lead)
            cards.append({"lead": lead, "subject": subject, "body": body,
                          "own_draft": bool(lead.outreach_draft), "cc": lead.cc_emails})

    return render(request, "signals/operator/outreach.html", {
        "tab": tab, "cards": cards, "counts": counts,
        "shown_count": len(shown), "total_count": total, "show_all": show_all,
        "limit": _OUTREACH_LIMIT,
        "sent_count": SalesLead.objects.filter(email_status="sent").count(),
    })


@_operator_required
@require_POST
def operator_outreach_contacted(request, pk):
    """Mark a Call List lead as contacted — drops it off the to-call worklist and
    advances its pipeline stage to Contacted."""
    from django.urls import reverse
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import advance_to_contacted
    lead = get_object_or_404(SalesLead, pk=pk)
    lead.email_status = "sent"
    advance_to_contacted(lead)
    lead.save(update_fields=["email_status", "status", "updated_at"])
    messages.success(request, f"Marked {lead.name} as contacted.")
    return redirect(f"{reverse('operator-outreach')}?tab=call")


def _outreach_redirect(request):
    """After a save/send, return to the tab the operator was working on
    (warm/cold/call) instead of dumping them back on the default Warm tab."""
    from django.urls import reverse
    tab = request.POST.get("tab", "warm")
    if tab not in ("warm", "cold", "call"):
        tab = "warm"
    return redirect(f"{reverse('operator-outreach')}?tab={tab}")


@_operator_required
@require_POST
def operator_outreach_save(request, pk):
    """Save the operator's edited subject/body for a lead (no send)."""
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import parse_cc
    lead = get_object_or_404(SalesLead, pk=pk)
    lead.subject_line = request.POST.get("subject", "").strip()[:255]
    lead.outreach_draft = request.POST.get("body", "")
    lead.cc_emails = ", ".join(parse_cc(request.POST.get("cc", "")))[:500]
    lead.save(update_fields=["subject_line", "outreach_draft", "cc_emails", "updated_at"])
    messages.success(request, f"Draft saved for {lead.name}.")
    return _outreach_redirect(request)


@_operator_required
@require_POST
def operator_outreach_send(request, pk):
    """Send the (possibly edited) email to one lead and mark it sent."""
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import send_outreach_email

    lead = get_object_or_404(SalesLead, pk=pk)
    if lead.email_status == "sent":
        messages.info(request, f"{lead.name} was already emailed.")
        return _outreach_redirect(request)
    if not lead.email:
        messages.error(request, f"{lead.name} has no email address.")
        return _outreach_redirect(request)
    subject = request.POST.get("subject", "").strip()
    body = request.POST.get("body", "")
    cc = request.POST.get("cc", "").strip()
    try:
        send_outreach_email(lead, subject, body, cc=cc)
        cc_note = f" (cc: {lead.cc_emails})" if lead.cc_emails else ""
        messages.success(request, f"Sent to {lead.name} <{lead.email}>{cc_note}.")
    except Exception as exc:
        messages.error(request, f"Send failed for {lead.name}: {exc}")
    return _outreach_redirect(request)


@_operator_required
@require_POST
def operator_outreach_mark_sent(request, pk):
    """Mark a lead as already sent WITHOUT sending — for emails you sent by hand
    (e.g. from Gmail). Clears it off the queue so it can't be double-sent, and
    advances its pipeline stage to Contacted."""
    from openoutreach.signals.models import SalesLead
    from openoutreach.signals.outreach import advance_to_contacted
    lead = get_object_or_404(SalesLead, pk=pk)
    lead.email_status = "sent"
    advance_to_contacted(lead)
    lead.save(update_fields=["email_status", "status", "updated_at"])
    messages.success(request, f"Marked {lead.name or lead.organization} as already sent.")
    return _outreach_redirect(request)


@_operator_required
@require_POST
def operator_outreach_remove(request, pk):
    """Remove a lead from the outreach queue — a soft skip (hidden from the
    cockpit, kept in the database and recoverable via Django Admin) that also
    archives it in the pipeline."""
    from openoutreach.signals.models import SalesLead
    lead = get_object_or_404(SalesLead, pk=pk)
    lead.email_status = "skipped"
    lead.status = SalesLead.Status.PASSED
    lead.save(update_fields=["email_status", "status", "updated_at"])
    messages.success(request, f"Removed {lead.name or lead.organization} from the list.")
    return _outreach_redirect(request)


@_operator_required
def operator_market(request):
    """Florida Market browser — the 114k-org prospect universe."""
    from django.core.paginator import Paginator
    from django.db.models import Q

    from openoutreach.signals.models import CountyRollout, FloridaOrg

    county = request.GET.get("county", "").strip()
    region = request.GET.get("region", "").strip()
    sector = request.GET.get("sector", "").strip()
    min_assets = request.GET.get("min_assets", "").strip()
    q = request.GET.get("q", "").strip()
    priority = request.GET.get("priority", "").strip()
    has_contact = request.GET.get("has_contact", "").strip()
    serves = request.GET.get("serves", "").strip()

    qs = FloridaOrg.objects.all()
    if serves:
        qs = qs.filter(service_area=serves)
    if priority:
        qs = qs.filter(priority=priority)
    if has_contact:
        qs = qs.filter(
            Q(website__gt="") | Q(phone__gt="") | Q(contact_email__gt="")
            | Q(principal_officer__gt="")
        )
    if county:
        qs = qs.filter(county=county)
    if region:
        qs = qs.filter(region=region)
    if sector:
        qs = qs.filter(ntee_sector=sector)
    if min_assets:
        try:
            qs = qs.filter(asset_amount__gte=int(min_assets.replace(",", "")))
        except ValueError:
            min_assets = ""
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(ein__icontains=q))

    paginator = Paginator(qs.select_related("promoted_lead"), 50)
    page = paginator.get_page(request.GET.get("page"))

    # Display helpers computed server-side (no template filters needed).
    from openoutreach.signals.market import compact_amount, website_domain
    for org in page.object_list:
        org.assets_compact = compact_amount(org.asset_amount)
        org.income_compact = compact_amount(org.income_amount)
        org.website_label = website_domain(org.website)

    if paginator.count:
        page_summary = f"{page.start_index():,}–{page.end_index():,} of {paginator.count:,}"
    else:
        page_summary = "0 of 0"

    # Preserve current filters in pagination/promote links.
    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    counties = list(
        CountyRollout.objects.order_by("county").values_list("county", flat=True)
    ) or list(
        FloridaOrg.objects.exclude(county="").order_by("county")
        .values_list("county", flat=True).distinct()
    )
    regions = list(
        FloridaOrg.objects.exclude(region="").order_by("region")
        .values_list("region", flat=True).distinct()
    )
    sectors = list(
        FloridaOrg.objects.exclude(ntee_sector="").order_by("ntee_sector")
        .values_list("ntee_sector", flat=True).distinct()
    )

    total_orgs = FloridaOrg.objects.count()
    ctx = {
        "page": page,
        "total_orgs": total_orgs,
        "filtered_count": paginator.count,
        "promoted_count": FloridaOrg.objects.filter(promoted_lead__isnull=False).count(),
        "counties": counties,
        "regions": regions,
        "sectors": sectors,
        "county_filter": county,
        "region_filter": region,
        "sector_filter": sector,
        "priority_filter": priority,
        "has_contact": has_contact,
        "priorities": list(
            FloridaOrg.objects.exclude(priority="").order_by("priority")
            .values_list("priority", flat=True).distinct()
        ),
        "serves_filter": serves,
        "service_areas": list(
            FloridaOrg.objects.exclude(service_area="").order_by("service_area")
            .values_list("service_area", flat=True).distinct()
        ),
        "min_assets": min_assets,
        "q": q,
        "querystring": querystring,
        "page_summary": page_summary,
        "total_orgs_fmt": f"{total_orgs:,}",
        "filtered_count_fmt": f"{paginator.count:,}",
    }
    return render(request, "signals/operator/market.html", ctx)


@_operator_required
@require_POST
def operator_market_promote(request, pk):
    from openoutreach.signals.market import promote_org_to_pipeline
    from openoutreach.signals.models import FloridaOrg

    org = get_object_or_404(FloridaOrg, pk=pk)
    lead, created = promote_org_to_pipeline(org)
    if created:
        messages.success(request, f"Added {org.name} to the pipeline (Cold — Florida CRM).")
    else:
        messages.warning(request, f"{org.name} is already in the pipeline.")
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    url = reverse("operator-market")
    next_qs = request.POST.get("next", "")
    if next_qs:
        url += f"?{next_qs}"
    return HttpResponseRedirect(url)


@_operator_required
def operator_market_counties(request):
    """County Rollout board — the 67-county build-out plan."""
    from openoutreach.signals.models import CountyRollout

    sort = request.GET.get("sort", "county")
    allowed = {
        "county": "county",
        "tier": "rollout_tier",
        "region": "region",
        "owner": "owner",
        "status": "status",
        "nonprofits": "-nonprofit_count",
        "priority": "-high_priority_count",
        "funders": "-funder_starter_count",
    }
    order = allowed.get(sort, "county")
    counties = list(CountyRollout.objects.order_by(order, "county"))
    for c in counties:
        c.nonprofit_fmt = f"{c.nonprofit_count:,}"
        c.high_priority_fmt = f"{c.high_priority_count:,}"
        c.funder_starter_fmt = f"{c.funder_starter_count:,}"
    ctx = {"counties": counties, "sort": sort if sort in allowed else "county"}
    return render(request, "signals/operator/market_counties.html", ctx)


@_operator_required
def operator_waitlist(request):
    try:
        from openoutreach.signals.models import InterestSignup
        signups = InterestSignup.objects.order_by("-created_at")
        nurture_counts = {
            "step_0": signups.filter(nurture_step=0).count(),
            "step_1": signups.filter(nurture_step=1).count(),
            "step_2": signups.filter(nurture_step=2).count(),
            "step_3": signups.filter(nurture_step=3).count(),
        }
        status_counts = {
            s.value: signups.filter(status=s).count()
            for s in InterestSignup.Status
        }
    except Exception:
        signups = []
        nurture_counts = {}
        status_counts = {}

    ctx = {"signups": signups, "nurture_counts": nurture_counts, "status_counts": status_counts}
    return render(request, "signals/operator/waitlist.html", ctx)
