"""Operator outreach cockpit: compose deterministic drafts, edit, and send
server-side (replaces the local n8n digest). Staff-gated; every send is a
deliberate per-lead action, never an automated blast.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from openoutreach.signals.models import SalesLead
from openoutreach.signals.outreach import compose_outreach_email, outreach_queue

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(username="ops", password="x", is_staff=True)


def _lead(**kw):
    defaults = dict(name="Dana Reed", organization="Bright Paths", email="dana@brightpaths.org",
                    list_segment="warm", warmth="hot", email_status="not_sent")
    defaults.update(kw)
    return SalesLead.objects.create(**defaults)


# ── compose ───────────────────────────────────────────────────────────────────

def test_compose_warm_vs_cold_and_video():
    warm = _lead(list_segment="warm", why_fit="we worked together at Aeras")
    subject, body = compose_outreach_email(warm)
    assert "Dana" in body
    assert "we worked together at Aeras" in body
    assert "youtu.be/FBvLg9c35Qo" in body  # sales walkthrough always present
    assert "cal.com/marcus-scott-br7maf/founder-walkthrough" in body  # calendar booking link
    assert "Bright Paths" in subject

    cold = _lead(name="Sam Cole", organization="Metro Coalition", email="s@metro.org",
                 list_segment="cold_florida_crm", warmth="cold")
    _s, cold_body = compose_outreach_email(cold)
    assert "founder of Anansi Atlas" in cold_body  # cold opener
    assert "anansiatlas.com" in cold_body                         # website in signature
    assert "linkedin.com/company/anansi-atlas" in cold_body       # LinkedIn in signature


def test_saved_edit_used_over_fresh_compose():
    from openoutreach.signals.outreach import draft_for
    lead = _lead(outreach_draft="My hand-edited version.")
    _subject, body = draft_for(lead)
    assert body == "My hand-edited version."


# ── queue ordering ────────────────────────────────────────────────────────────

def test_queue_hottest_first_and_excludes_sent_and_no_email():
    _lead(name="A Cold", organization="Zeta", email="a@z.org", list_segment="cold_florida_crm", warmth="cold")
    _lead(name="B Hot", organization="Alpha", email="b@a.org", list_segment="warm", warmth="hot")
    _lead(name="C Sent", organization="Beta", email="c@b.org", email_status="sent")
    _lead(name="D NoEmail", organization="Gamma", email="", list_segment="warm", warmth="hot")
    queue = outreach_queue()
    names = [l.name for l in queue]
    assert names == ["B Hot", "A Cold"]  # warm-hot first, cold last; sent + no-email excluded


# ── cockpit page + gating ─────────────────────────────────────────────────────

def test_cockpit_lists_leads_for_staff(client, staff):
    _lead()
    client.force_login(staff)
    body = client.get(reverse("operator-outreach")).content.decode()
    assert "Dana Reed" in body
    assert "youtu.be/FBvLg9c35Qo" in body
    assert "Send" in body


def test_pipeline_draft_button_falls_back_to_template_without_llm_key(client, staff):
    # No LLM key configured (the common setup) → the Pipeline "Draft" button must
    # NOT error; it falls back to the deterministic composer and produces a draft.
    lead = _lead(name="Cold Carl", organization="Metro Coalition", email="c@metro.org",
                 list_segment="cold_florida_crm", warmth="cold", source="cold")
    client.force_login(staff)
    response = client.post(reverse("operator-pipeline-draft", kwargs={"pk": lead.pk}))
    assert response.status_code == 302
    lead.refresh_from_db()
    assert lead.outreach_draft                         # a draft was produced, not an error
    assert "founder of Anansi Atlas" in lead.outreach_draft   # the cold template body


def test_org_website_from_email_domain():
    from openoutreach.signals.outreach import org_website
    w = org_website(_lead(email="info@arnettehouse.org", organization="Arnette House"))
    assert w["url"] == "https://arnettehouse.org" and w["search"] is False


def test_org_website_falls_back_to_search_for_freemail():
    from openoutreach.signals.outreach import org_website
    w = org_website(_lead(email="normanls@earthlink.net", organization="Garden Worship Center"))
    assert w["search"] is True
    assert "google.com/search" in w["url"] and "Garden" in w["url"]


def test_cockpit_shows_the_org_website_link(client, staff):
    _lead(email="info@arnettehouse.org", organization="Arnette House",
          list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    body = client.get(reverse("operator-outreach") + "?tab=cold").content.decode()
    assert "https://arnettehouse.org" in body          # a real clickable website link
    assert "Website" in body


def test_cockpit_requires_staff(client):
    user = get_user_model().objects.create_user(username="notstaff", password="x")
    client.force_login(user)
    response = client.get(reverse("operator-outreach"))
    assert response.status_code in (302, 403)  # staff_member_required bounces


# ── tabs: warm / cold / call ──────────────────────────────────────────────────

def test_tabs_partition_leads_by_segment(client, staff):
    _lead(name="Warm Wanda", organization="Warm Org", email="w@w.org",
          list_segment="warm", warmth="hot")
    _lead(name="Cold Carl", organization="Cold Org", email="c@c.org",
          list_segment="cold_florida_crm", warmth="cold")
    _lead(name="Call Cathy", organization="Phone Org", email="",
          list_segment="cold_call_list", phone="(352) 555-0100",
          outreach_draft="Hi, this is Marcus from Anansi Atlas...")
    client.force_login(staff)

    warm = client.get(reverse("operator-outreach") + "?tab=warm").content.decode()
    assert "Warm Wanda" in warm and "Cold Carl" not in warm and "Call Cathy" not in warm

    cold = client.get(reverse("operator-outreach") + "?tab=cold").content.decode()
    assert "Cold Carl" in cold and "Warm Wanda" not in cold

    call = client.get(reverse("operator-outreach") + "?tab=call").content.decode()
    assert "Phone Org" in call
    assert "(352) 555-0100" in call
    assert "Hi, this is Marcus from Anansi Atlas..." in call  # script shown
    assert "Mark contacted" in call


def test_default_tab_is_warm(client, staff):
    _lead(name="Warm Wanda", organization="Warm Org", email="w@w.org", list_segment="warm")
    _lead(name="Cold Carl", organization="Cold Org", email="c@c.org",
          list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    body = client.get(reverse("operator-outreach")).content.decode()
    assert "Warm Wanda" in body and "Cold Carl" not in body


def test_email_tab_caps_at_twenty_with_show_all(client, staff):
    for i in range(25):
        _lead(name=f"Warm {i:02d}", organization=f"Org {i:02d}",
              email=f"w{i:02d}@w.org", list_segment="warm", warmth="warm")
    client.force_login(staff)

    capped = client.get(reverse("operator-outreach") + "?tab=warm").content.decode()
    assert capped.count('class="oc-card"') == 20
    assert "Show all 25" in capped

    everything = client.get(reverse("operator-outreach") + "?tab=warm&all=1").content.decode()
    assert everything.count('class="oc-card"') == 25


def test_mark_sent_clears_lead_without_sending(client, staff):
    # For emails sent by hand: mark as sent, no email goes out, drops off the tab.
    lead = _lead(name="Warm Wanda", organization="WO", email="w@w.org", list_segment="warm")
    client.force_login(staff)
    resp = client.post(reverse("operator-outreach-mark-sent", kwargs={"pk": lead.pk}), {"tab": "warm"})
    assert resp.status_code == 302 and resp.url.endswith("?tab=warm")
    assert len(mail.outbox) == 0                        # nothing was sent
    lead.refresh_from_db()
    assert lead.email_status == "sent"
    body = client.get(reverse("operator-outreach") + "?tab=warm").content.decode()
    assert "w@w.org" not in body                        # off the list (email only shows in cards)


def test_remove_soft_hides_lead_from_the_tab(client, staff):
    lead = _lead(name="Cold Carl", organization="Metro Coalition", email="c@metro.org",
                 list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    resp = client.post(reverse("operator-outreach-remove", kwargs={"pk": lead.pk}), {"tab": "cold"})
    assert resp.status_code == 302 and resp.url.endswith("?tab=cold")
    lead.refresh_from_db()
    assert lead.email_status == "skipped"               # soft-removed, still in DB
    assert SalesLead.objects.filter(pk=lead.pk).exists()
    body = client.get(reverse("operator-outreach") + "?tab=cold").content.decode()
    assert "Metro Coalition" not in body                # hidden from the cockpit


def test_mark_contacted_drops_call_lead_off_the_list(client, staff):
    lead = _lead(name="Call Cathy", organization="Phone Org", email="",
                 list_segment="cold_call_list", phone="(352) 555-0100")
    client.force_login(staff)
    response = client.post(reverse("operator-outreach-contacted", kwargs={"pk": lead.pk}))
    assert response.status_code == 302
    assert len(mail.outbox) == 0  # calling never sends email
    lead.refresh_from_db()
    assert lead.email_status == "sent"
    call = client.get(reverse("operator-outreach") + "?tab=call").content.decode()
    assert "Phone Org" not in call


# ── send + save ───────────────────────────────────────────────────────────────

def test_send_emails_lead_marks_sent(client, staff, settings):
    # Reply-To stamping is covered by test_email_reply_to.py; here the test
    # runner's locmem backend captures the message so we assert send + mark.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    client.force_login(staff)
    response = client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                           {"subject": "Hi Dana", "body": "Edited body here."})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["dana@brightpaths.org"]
    assert msg.subject == "Hi Dana"
    assert "Edited body here." in msg.body
    lead.refresh_from_db()
    assert lead.email_status == "sent"
    assert lead.outreach_draft == "Edited body here."


def test_outreach_sends_from_mail_bcc_marcus(client, staff, settings):
    # Warm and cold both send from mail@ (main) and BCC marcus@ so a copy of the
    # whole trail lands in Marcus's one inbox. Reply-To (marcus@) is stamped by
    # the backend (covered in test_email_reply_to.py).
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    warm = _lead(name="Pat Warm", organization="Warm Org", email="pat@warm.org",
                 list_segment="warm", warmth="hot")
    cold = _lead(name="Sam Cold", organization="Cold Org", email="sam@cold.org",
                 list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": warm.pk}),
                {"subject": "hi", "body": "b"})
    client.post(reverse("operator-outreach-send", kwargs={"pk": cold.pk}),
                {"subject": "hi", "body": "b"})
    by_to = {m.to[0]: m for m in mail.outbox}
    for m in by_to.values():
        assert m.from_email == "mail@anansiatlas.com"
        assert "marcus@anansiatlas.com" in m.bcc


def test_cc_adds_recipients_to_the_thread(client, staff):
    lead = _lead(email="dana@brightpaths.org")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b", "cc": "board@brightpaths.org, ceo@brightpaths.org"})
    msg = mail.outbox[0]
    assert msg.to == ["dana@brightpaths.org"]
    assert msg.cc == ["board@brightpaths.org", "ceo@brightpaths.org"]
    lead.refresh_from_db()
    assert lead.cc_emails == "board@brightpaths.org, ceo@brightpaths.org"


def test_cc_dedupes_the_primary_recipient(client, staff):
    lead = _lead(email="dana@brightpaths.org")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b", "cc": "dana@brightpaths.org, board@brightpaths.org"})
    msg = mail.outbox[0]
    assert msg.cc == ["board@brightpaths.org"]  # primary not CC'd twice


def test_send_advances_pipeline_stage_to_reached_out(client, staff, settings):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead(email="dana@brightpaths.org")
    assert lead.status == "new"
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b", "tab": "warm"})
    lead.refresh_from_db()
    assert lead.status == "reached_out"                # pipeline stage advanced


def test_send_does_not_knock_back_an_advanced_lead(client, staff, settings):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead(email="dana@brightpaths.org", status="closed")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b", "tab": "warm"})
    lead.refresh_from_db()
    assert lead.status == "closed"                     # not knocked backward to reached_out


def test_mark_sent_also_advances_stage_to_reached_out(client, staff):
    lead = _lead(email="w@w.org", list_segment="warm")
    client.force_login(staff)
    client.post(reverse("operator-outreach-mark-sent", kwargs={"pk": lead.pk}), {"tab": "warm"})
    lead.refresh_from_db()
    assert lead.status == "reached_out"


def test_remove_passes_lead_in_pipeline(client, staff):
    lead = _lead(email="c@metro.org", list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    client.post(reverse("operator-outreach-remove", kwargs={"pk": lead.pk}), {"tab": "cold"})
    lead.refresh_from_db()
    assert lead.email_status == "skipped" and lead.status == "passed"


def test_send_is_idempotent_no_double_send(client, staff):
    lead = _lead(email_status="sent")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "x", "body": "y"})
    assert len(mail.outbox) == 0  # already sent → skipped


def test_save_returns_to_the_tab_you_were_on(client, staff):
    # Editing a cold email and saving must keep you on the Cold tab, not bounce
    # to the default Warm tab (that made edits look like they didn't work).
    lead = _lead(name="Cold Carl", organization="Metro", email="c@metro.org",
                 list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    resp = client.post(reverse("operator-outreach-save", kwargs={"pk": lead.pk}),
                       {"subject": "s", "body": "edited body", "tab": "cold"})
    assert resp.status_code == 302
    assert resp.url.endswith("?tab=cold")
    lead.refresh_from_db()
    assert lead.outreach_draft == "edited body"      # and the edit persisted


def test_send_returns_to_the_tab_you_were_on(client, staff):
    lead = _lead(name="Cold Carl", organization="Metro", email="c@metro.org",
                 list_segment="cold_florida_crm", warmth="cold")
    client.force_login(staff)
    resp = client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                       {"subject": "s", "body": "b", "tab": "cold"})
    assert resp.status_code == 302
    assert resp.url.endswith("?tab=cold")


def test_outreach_redirect_defaults_to_warm_for_bad_tab(client, staff):
    lead = _lead(email="d@d.org")
    client.force_login(staff)
    resp = client.post(reverse("operator-outreach-save", kwargs={"pk": lead.pk}),
                       {"subject": "s", "body": "b", "tab": "bogus"})
    assert resp.url.endswith("?tab=warm")            # invalid tab falls back safely


def test_save_draft_persists_without_sending(client, staff):
    lead = _lead()
    client.force_login(staff)
    client.post(reverse("operator-outreach-save", kwargs={"pk": lead.pk}),
                {"subject": "Draft subject", "body": "Draft body, not sent."})
    assert len(mail.outbox) == 0
    lead.refresh_from_db()
    assert lead.outreach_draft == "Draft body, not sent."
    assert lead.subject_line == "Draft subject"
    assert lead.email_status == "not_sent"
