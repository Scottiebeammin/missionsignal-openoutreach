"""Write verified, researched profiles onto cold leads so drafts stop guessing.

Why this exists
---------------
``preview_cohort_drafts`` passed ``company_intel=""`` — the intel section of the
prompt collapsed entirely, and the model was writing from the organization's
*legal name and IRS NTEE sector code alone*. With nothing else to work with it
filled the gap with whatever was plausible for that kind of nonprofit, which is
how a residential diabetes camp got pitched Florida DOE's 21st Century Community
Learning Centers, and how a pregnancy center was told money was "already
earmarked" for its work.

The fix is data, not prompt wording. ``_lead_facts`` already feeds ``notes`` and
``why_fit`` into the prompt, so a researched profile on those two fields reaches
the model with no migration and no template change.

Every line below was verified against the organization's own site or its IRS
Form 990 in August 2026, by web research. Where sources conflicted, the
organization's own site won and the conflict is noted. Where nothing could be
verified, the field says so rather than guessing — an absent fact is safe, an
invented one is not.

Re-runnable and keyed by email, so re-running overwrites cleanly. Facts decay:
re-verify before reusing these profiles in a much later campaign.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

# email -> (notes, why_fit)
#
# NOTES is the factual profile. It always states plainly whether the org runs
# out-of-school-time programming, because that single question is what the
# 21st CCLC misfires turned on — the model may only name that program for an org
# whose profile says YES, and every org below says NO.
#
# WHY_FIT is the honest read on whether Atlas actually helps them, including
# when the answer is "not much". A weak fit stated plainly produces a humbler,
# truer email than a strong fit invented.
INTEL: dict[str, tuple[str, str]] = {
    "hello@gracemarketplace.org": (
        "Operates as GRACE Marketplace. A single low-barrier homeless services campus in "
        "Gainesville: 184 emergency shelter beds across four programs (men, women, couples, "
        "veterans), plus day services, street outreach and housing placement. On-site: Café 131 "
        "meal service, Grace Clinic & Pharmacy, GRACE Boutique, computer lab, Grace Grows Garden, "
        "an animal welfare program for residents' pets, and Dignity Village. "
        "SERVES: adults 18+ ONLY — they explicitly do not serve families with children and refer "
        "them to St. Francis House, Family Promise, or 211. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — adults only, no youth programming of any kind. "
        "SCALE: FY2025 revenue $5.81M, expenses $5.44M. "
        "GOVERNMENT FUNDING: substantial and named — City of Gainesville, Alachua County, US Dept "
        "of Veterans Affairs, HUD. "
        "RECENT: leadership churn — Darius Williams named permanent CEO Sept 2025, Mark Bonner "
        "appointed interim CEO June 2026. Absorbed demand from St. Francis House's wind-down. "
        "Publicly signalled service reductions amid city budget cuts.",

        "Strong fit. They are deeply dependent on a handful of city and county contracts and have "
        "publicly signalled service cuts as those budgets tighten — the exact situation where "
        "seeing the wider funding map matters. Handle the leadership churn carefully: do not "
        "address a named CEO, and note the contact address is a generic hello@.",
    ),
    "info@arnettehouse.org": (
        "24-hour Emergency Youth Shelter in Ocala (2310 NE 24th St) plus two long-term foster group "
        "homes and a non-residential Community Counseling program staffed by master's-level "
        "counselors. Also runs SNAP (Stop Now and Plan), Safe Place, CINS/FINS, and domestic "
        "violence / juvenile probation respite as an alternative to secure detention. "
        "SERVES: youth 6–17 across the 5th Circuit (Marion, Lake, Sumter, Citrus, Hernando). "
        "Shelter 10–17, group homes 12–17, SNAP 6–11. Runaway, lockout, homeless, abandoned, "
        "truant youth and youth in family conflict. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — SNAP is a 13-week clinical behavioural curriculum "
        "(anger management, self-control, bullying prevention), not academic enrichment. No "
        "after-school, tutoring or summer academic programming exists. "
        "SCALE: FY2025 revenue $4.23M, expenses $3.47M; 56% contributions, 25% program service "
        "revenue. Their own site says the shelter serves approx. 360 children/year (a secondary "
        "source claims 500+ — use 360). "
        "GOVERNMENT FUNDING: HHS Family and Youth Services Bureau grant; Florida DJJ contract for "
        "CINS/FINS; Florida DCF for shelter and group homes. The CINS/FINS contract is funded with "
        "General Revenue through June 30, 2026. "
        "RECENT: scored 100% overall compliance (13 of 13 indicators) on the Florida Network / DJJ "
        "CINS/FINS monitoring tool, dated Jan 28, 2026.",

        "Strong fit, and the sharpest hook on the list: their CINS/FINS contract is General "
        "Revenue-funded through a specific date, June 30, 2026. A dated funding cliff on a named "
        "contract is exactly the situation where knowing what else exists is worth something.",
    ),
    "info@elcalachua.org": (
        "Florida's designated early learning coalition for Alachua County. NOT a direct childcare "
        "provider — it is a subsidy administrator and referral agency. Determines eligibility and "
        "pays child care tuition subsidies through School Readiness and Childcare Tuition "
        "Assistance, registers children for state-funded VPK, runs free Child Care Resource & "
        "Referral, and administers curriculum enhancement and provider payments. "
        "SERVES: Alachua County families and child care providers. VPK covers children who are 4 "
        "by Sept 1; School Readiness covers families at or below 55% of State Median Income. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — and this matters. ELCAC operates no programming "
        "directly at all. Its referral service points families toward afterschool programs and its "
        "subsidy dollars can flow to school-age care at contracted providers, but it runs none "
        "itself. It is a funder and referral channel, not an operator. "
        "SCALE: FY2025 revenue $19.28M, expenses $19.26M — essentially all pass-through subsidy. "
        "GOVERNMENT FUNDING: this IS their funding — federal and Alachua County money for School "
        "Readiness, Florida DOE / Division of Early Learning for VPK, plus City of Gainesville and "
        "City of Waldo. Subject to federal single audit. "
        "RECENT: relocated to 201 SE 2nd Ave, Suite 201, downtown Gainesville (Oct 2025). "
        "Partnership with UF Lastinger Center for Learning (Nov 2025). CEO Xaviera White.",

        "Weak fit as a funding-discovery customer — they are themselves a pass-through funder, and "
        "almost all their revenue is already state and federal money they administer. Do not pitch "
        "them the funding-visibility gap; they live inside it professionally. The only honest angle "
        "is Atlas as something useful to the provider network they serve. If that angle does not "
        "land, this lead is better dropped than forced. "
        "DO NOT MENTION: their FY2024 independent audit flagged an internal control deficiency.",
    ),
    "info@wpcocala.com": (
        "Legal name Education For Life, Inc.; operates as Women's Pregnancy Center. One facility at "
        "1701 E Silver Springs Blvd, Ocala. Christ-centered pregnancy center providing free "
        "pregnancy tests, limited obstetric ultrasounds, options counselling, STI information and "
        "post-abortion support. Seven-week in-person parenting programme (or 16 emailed videos); "
        "participants earn 'Baby Bucks' redeemable in the on-site Boutique for diapers, wipes, "
        "clothing, formula and car seats. "
        "SERVES: women and men facing pregnancy decisions in Marion County, plus expectant and new "
        "parents. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. Note the legal name 'Education For Life' is a false "
        "signal — all their education is adult parenting and pregnancy curriculum. There is no K-12 "
        "or youth programming. "
        "SCALE: FY2025 revenue approx. $891.9K, expenses approx. $749.9K. "
        "GOVERNMENT FUNDING: NONE FOUND — 97.6% of revenue is private contributions ($870K of "
        "$892K). No government grant appears on their site or in their 990. "
        "RECENT: nothing found in the last 18 months.",

        "Weak fit, and the state/county funding pitch is close to wrong for them: they run on "
        "private contributions almost entirely and take no government money we can find. "
        "CRITICAL — NEVER claim funding is 'earmarked' or set aside for pregnancy support work. "
        "That claim is false, we cannot support it, and it has already appeared in a draft to this "
        "lead once. If anything is offered here it is visibility into private and foundation "
        "funders, not government money.",
    ),
    "info@floridadiabetescamp.org": (
        "Operates as Florida Diabetes Camp. Runs residential (overnight) medical-specialty camp "
        "sessions and year-round weekend sessions across Florida for children with type 1 diabetes, "
        "staffed by pediatric endocrinologists and APRNs. Sites include Dogwood Acres (Chipley), "
        "Rotary's Camp Florida (Brandon), YMCA Camp Winona (De Leon Springs) and a cycling route "
        "out of Branford. ACA-accredited. Incorporated 1970. "
        "NAMED SESSIONS: Pee-Wee Camp, Adventure Cycling Camp, Fun Sports Camp, Camp Winona "
        "Sessions 1 and 2, Teen Weekend, Sam Fuld's T1D Sports Camp, family and bring-a-friend "
        "weekends. "
        "SERVES: children and teens with type 1 diabetes, ages 5–18, in age-banded sessions, plus "
        "families and siblings. Their About page reports 500+ youngsters at six summer sessions and "
        "another 700 in weekend sessions. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. This is residential medical camp — the curriculum is "
        "diabetes self-management and psychosocial support. It is NOT after-school or academic "
        "enrichment, and 21st CCLC has no application here whatsoever. "
        "SCALE: approx. $2.0M revenue, $1.6M assets FY2024. Medical Director Paul Hiers MD; VP of "
        "Operations Casey Golden. 23 pediatric endocrinologists/APRNs volunteer as medical staff. "
        "GOVERNMENT FUNDING: NONE — and they say so themselves. Their About page states the "
        "organization 'does not receive any governmental money nor is it underwritten by any "
        "national diabetes organization.'",

        "Moderate fit, but the standard pitch is wrong for them. They state on their own website "
        "that they take no government money at all, so leading with the state-and-county funding "
        "gap tells them we did not read their site. The honest angle is private, foundation and "
        "health-system funding — and the fact that they self-fund is worth acknowledging directly "
        "rather than talking past. "
        "NEVER name 21st CCLC or any education program to this lead.",
    ),
    "llewis@habitatocala.org": (
        "IMPORTANT: the IRS record says 'Habitat For Humanity International Inc' but this lead is "
        "the LOCAL affiliate — Habitat for Humanity of Marion County. Address them as the local "
        "affiliate, never as the national organization. "
        "Builds and sells affordable homes to income-qualified Marion County families using a "
        "Community Land Trust model, requiring 350 hours of sweat equity plus homebuyer education. "
        "Builds in the City of Ocala, Silver Springs Shores, Marion Oaks and Dunnellon. Operates "
        "two ReStore home-improvement resale stores (10800 SW 91st Ave and 926 NW 27th Ave). "
        "Application-to-closing runs 12–18 months. "
        "SERVES: low-to-moderate-income Marion County households seeking homeownership — adults and "
        "families, not a youth-serving population. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. (Phoenix Rising YouthBuild builds their homes but is "
        "run by CareerSource CLM with Eckerd Connects, serves ages 18–24, and is not theirs.) "
        "NAMED EVENTS: Women Build, Bowl2Build, Strawberry Festival, 250 for 250 Variety Show. "
        "SCALE: staff count and budget not published on their own site. "
        "GOVERNMENT FUNDING: none named on their own site. "
        "RECENT: Women Build 2025 / Realtor 'Raising the Wall' build Sept 2025 for two West Ocala "
        "families.",

        "Strong fit. Affordable housing is one of the areas where county and state money — SHIP, "
        "CDBG, HOME — is real, recurring and administered locally rather than posted federally, and "
        "nothing on their site suggests they are tracking it. Address the Marion County affiliate, "
        "not Habitat International.",
    ),
    "rdwray@harvestinternational.org": (
        "A non-denominational Christian missions-sending ministry with an administrative office in "
        "Ocala (PO Box 6690). Provides administrative and logistical support for long-term "
        "missionaries serving overseas, organises short-term mission trips, supports Christian "
        "orphanages and schools abroad with food and school fees, and ships containers of goods "
        "overseas. "
        "SERVES: the missionaries it sends (adults), and impoverished children and communities "
        "OVERSEAS. No Florida beneficiary population is described anywhere. "
        "WHERE THEY WORK: NOT Florida. Only the admin office is here. All programme delivery is "
        "international — reported countries include Cuba, Haiti, India, Jamaica, Kenya, Romania, "
        "Uganda, Ukraine, US Virgin Islands and Zimbabwe. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — no US-based youth programming of any kind. "
        "SCALE: approx. $196K revenue, $202K expenses (2024); 10 named missionaries on their site. "
        "GOVERNMENT FUNDING: none found.",

        "POOR FIT — recommend dropping this lead rather than emailing it. Anansi Atlas maps Florida "
        "state, county and local funding. This organisation delivers no programmes in Florida; it "
        "is a Florida-headquartered international missions org. Any claim that Atlas surfaces "
        "funding that fits their work would be a claim we cannot support. If it is emailed at all, "
        "the email must not imply we map international or missions funding.",
    ),
    "info@wellflorida.org": (
        "Healthy Start of North Central Florida Coalition. A maternal and child health coalition "
        "running home-visiting programmes across 12 north central Florida counties (Alachua, "
        "Bradford, Columbia, Dixie, Gilchrist, Hamilton, Lafayette, Levy, Marion, Putnam, Suwannee, "
        "Union). Nurse and paraprofessional home visits, childbirth and parenting education, doula "
        "support, newborn screening, father engagement, and Fetal & Infant Mortality Review. Also "
        "hosts a Mothers' Milk Bank donation site. "
        "WHY THE EMAIL DOMAIN DIFFERS: the coalition is an affiliate partner of WellFlorida Council, "
        "the state-designated local health council, which has housed it since 1992 and provides "
        "fiscal administration and staffing. The coalition keeps its own board. Staff therefore use "
        "@wellflorida.org addresses — the person behind this address is likely WellFlorida-employed "
        "staff working the coalition programme. "
        "NAMED PROGRAMS: Healthy Start, Parents as Teachers, Nurse-Family Partnership, NewboRN Home "
        "Visiting, T.E.A.M. DAD, Healthy Start Doula Program, Connect, Fetal & Infant Mortality "
        "Review. "
        "SERVES: pregnant women, new mothers, fathers, and families with children prenatal through "
        "age 3. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — every programme is prenatal-to-age-3 home visiting. "
        "Nothing touches K-12 students. "
        "GOVERNMENT FUNDING: they are one of 32 Healthy Start coalitions statewide and Florida's "
        "Healthy Start programme sits under the Florida Department of Health. No specific grant, "
        "contract or dollar figure could be verified — DO NOT CITE ONE. "
        "SCALE: not published.",

        "Moderate fit. They are already deeply plugged into state Department of Health funding, so "
        "the 'state money you cannot see' angle is weaker here than elsewhere — their likelier gap "
        "is private and foundation funding. Note the org name and email domain differ for a real "
        "reason; getting that relationship right signals we actually looked.",
    ),
    "info@kimberlyscenter.org": (
        "Operates as Kimberly's Center for Child Protection, at 2800 NE 14th Street, Ocala. Founded "
        "1996. A children's advocacy center giving child abuse and neglect victims a single "
        "child-friendly location for forensic interviews, in-house medical exams by their own "
        "pediatrician and APRNs, crisis intervention, and trauma-specialised individual and family "
        "therapy — so children do not repeat their story across agencies. Coordinates a "
        "multidisciplinary team with DCF, local law enforcement, the Child Protection Team and the "
        "Marion County Health Department. Also runs therapeutic supervised visitation and a "
        "prevention education curriculum delivered in schools. "
        "SERVES: children and teenagers in Marion County who are victims or alleged victims of "
        "abuse and neglect, plus non-offending family members. They do not publish an age range — "
        "do not cite one. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — their school touchpoint is prevention education "
        "delivered inside schools during the school day, not after-school or summer enrichment. "
        "SCALE: approx. 1,200–1,400 children per year; over 22,000 since 1996. Roughly 1,400 of the "
        "~4,000 suspected abuse cases reported annually in Marion County come through them. 25 "
        "employees. Executive Director Dawn Westgate, MNM. Accredited by the National Children's "
        "Alliance — one of 25 accredited centers in Florida. "
        "GOVERNMENT FUNDING: their Child Protection Team is funded by the Florida Department of "
        "Health. Government grants are one of several funding streams alongside private donors, "
        "corporate sponsors, foundations and events. No current amounts published. "
        "RECENT: ribbon cutting Feb 27, 2025 for a completed ~4,800 sq ft expansion — full therapy "
        "suite, trauma intervention advocacy rooms, additional offices, expanded lobby. Funded "
        "through a $1.6M capital campaign launched Jan 31, 2024, with roughly $800K still to raise "
        "at launch. Driver was rising case volume.",

        "Strongest fit on the list. They ran a $1.6M capital campaign with a substantial gap still "
        "open at launch, and case volume is rising — a concrete, dated, public need. The expansion "
        "is a legitimate and flattering thing to reference.",
    ),
    "info@marionliteracy.org": (
        "Adult literacy nonprofit in Ocala, founded 1999. Free one-on-one and small-group tutoring "
        "in basic reading and writing, GED preparation with individualised learning plans, and ESOL "
        "instruction from basic literacy through advanced grammar and pronunciation. Workshops in "
        "US citizenship, computer literacy, financial literacy, health literacy, and college and "
        "career coaching. Also runs volunteer tutoring inside the Marion County jail and trains "
        "inmates at Lowell Correctional Institution. "
        "SERVES: ADULTS aged 16 and older in Marion County, including ESOL students from over 20 "
        "countries and incarcerated adults. No K-12 population. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — this is exclusively adult education. Adult literacy "
        "tutoring is not out-of-school-time programming and there is no after-school, summer or "
        "K-12 enrichment anywhere in their work. "
        "SCALE: FY2025 revenue approx. $250K against approx. $246.6K expenses — a small "
        "organisation running close to break-even. Executive Director Yamila Acosta (since 2014). "
        "GOVERNMENT FUNDING: NONE FOUND. Every identified funder is private — Ocala Silver Springs "
        "Rotary Club Foundation ($47K, Aug 2025), United Way of Marion County, Dollar General "
        "Literacy Foundation ($8K, Dec 2024), Browder Family Foundation. "
        "DO NOT cite their street address — two sources conflict and a move could not be verified.",

        "Strong fit, and the most substantive insight on the list: they run entirely on small "
        "private grants and are close to break-even, while adult education is exactly the field "
        "where federal and state money flows through the state education agency rather than being "
        "posted where a small nonprofit would find it. The gap between a $250K budget funded by "
        "Rotary and Dollar General and the public adult-education funding stream is real and worth "
        "naming — carefully, without promising they would win any of it.",
    ),
    "admin@projecthopeocala.org": (
        "Faith-based nonprofit established 2007. Runs Hope Villas, a 40-unit two-bed/two-bath "
        "apartment complex in northeast Ocala where 32 units house homeless women and their "
        "children and 8 are rented at market rate to sustain the programme. On-site case manager, "
        "mental health counselling, financial skill development classes and trauma recovery "
        "services. First month free, then a subsidised fee stepping up toward market rent as the "
        "resident gains employment. Also runs the Hope Chest Thrift Store as a revenue source. "
        "SERVES: homeless women with children in Marion County. Homepage states 'housing 70+ "
        "survivors'. No age ranges published. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — children are present as residents' dependents, but "
        "the organisation runs only housing, case management and counselling. "
        "SCALE: FY ending June 2025 revenue $1.31M, expenses $1.00M, total assets $2.39M. CEO April "
        "McDonald. 8 staff and 12 board members. "
        "GOVERNMENT FUNDING: none found on their site or 990. A news report suggests they take no "
        "state or federal money, but that could not be verified — do not assert it. "
        "RECENT: Hope Chest Thrift Store opened March 2025, with some Hope Villas units converted "
        "from market rentals to programme units.",

        "Strong fit. They are deliberately building earned-revenue streams — market-rate units and "
        "a thrift store — to sustain the programme, which says they think hard about funding "
        "sustainability. Homeless housing also has real ESG, Continuum of Care and SHIP money "
        "administered locally.",
    ),
    "jross@arcalachua.org": (
        "Community-based provider for people with intellectual and developmental disabilities, on a "
        "campus at 3303 NW 83rd Street, Gainesville. Core operations are residential group homes — "
        "including ten homes specialising in adults with Prader-Willi syndrome, licensed by "
        "Florida's Agency for Persons with Disabilities — plus Adult Day Training and Adult Basic "
        "Education delivered with the Alachua County School Board. Runs revenue-generating "
        "vocational programmes: Gone4Ever Shredding, assembly and packaging work for local "
        "customers including the Alachua County Sheriff's Office, e-waste recycling, and LiveScan "
        "fingerprinting. "
        "SERVES: people with developmental and intellectual disabilities — intellectual disability, "
        "spina bifida, autism, cerebral palsy, Prader-Willi. About page says nearly 300 individuals "
        "across all ages; every named programme is adult-facing. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — all named programmes are adult services. "
        "SCALE: FY ending June 2025 revenue $12.83M, expenses $13.73M. Program services were 98.3% "
        "of revenue. "
        "GOVERNMENT FUNDING: HUD Section 811 for three rental units; group homes licensed by APD, "
        "which funds iBudget waiver services; Adult Basic Education through an Alachua County "
        "School Board partnership. "
        "RECENT: CEO transition — Johnny Adams became CEO effective June 22, 2026, succeeding Mark "
        "A. Swain. Cloretta Daniels promoted to Director of Programs June 2026.",

        "Strong fit and well-timed — a brand-new CEO three months into the job is exactly when "
        "someone takes a fresh look at the funding base, and theirs is heavily concentrated in APD "
        "waiver billing. "
        "HANDLE WITH CARE — DO NOT MENTION ANY OF THIS IN THE EMAIL: their FY2025 filing shows a "
        "net loss of roughly $895K, and they cancelled their October 2026 annual meeting citing "
        "inability to resource it. That context explains why the timing is good; referencing it "
        "would be insulting and would read as though we had been digging.",
    ),
    "recovery@zerohourlifecenter.org": (
        "A Recovery Community Organization founded 2016 by CEO Robert Cooper, headquartered at 3391 "
        "E Silver Springs Blvd, Suite G, Ocala. Delivers peer-based recovery support through "
        "certified peer specialists rather than clinical treatment, bridging people from "
        "professional treatment into long-term recovery. Recovery coaching, peer support meetings, "
        "a Peer Recovery Support Warm Line, monthly sober social events, jail and hospital bridge "
        "programmes in Sumter County, criminal reentry support, benefits enrolment as a DCF "
        "Community Partner, and a respite house. "
        "NAMED PROGRAMS: Recovery Coach, Peer Recovery Teen Program, Erik's Place (respite house, "
        "Citrus County), Hospital Bridge, Jail Bridge, Criminal Offender Re-Entry Initiative "
        "(CORI), Substance Exposed Newborns Prevention, Access Florida Benefits, SOAR, RescueWell "
        "(first responder peer support), Recovery on the Square. "
        "SERVES: adults in recovery from substance use disorder, people experiencing homelessness, "
        "justice-involved individuals, first responders, and families affected by substance-exposed "
        "newborns. Also teens — but their site and a regional directory give conflicting age ranges, "
        "so do not cite one. Covers Marion, Citrus, Lake, Sumter, Hernando, Alachua, Levy and "
        "Gilchrist counties. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — the teen programme is peer recovery support for "
        "substance use, not academic or after-school enrichment. "
        "SCALE: FY2024 revenue $1.09M, expenses $1.08M, total assets $34.3K. Program services were "
        "85.9% of revenue; contributions were just 1.4% ($15K). "
        "GOVERNMENT FUNDING: listed as a federal grant recipient with a most-recent award date of "
        "Sept 25, 2025, but agency, programme and amount could not be retrieved — do not name any. "
        "Florida DCF Community Partner designation. Jail and Hospital Bridge in Sumter County imply "
        "county agreements but no contract is named publicly.",

        "Strong fit, and the numbers make the case: 86% of their revenue is contracted program "
        "service revenue and only 1.4% is contributions, against total assets of $34K. An "
        "organisation that thin on reserves and that concentrated in contract revenue has a real "
        "reason to want visibility into what else exists. Do not quote their financials at them.",
    ),
}


class Command(BaseCommand):
    help = ("Write researched profiles onto cold leads (notes + why_fit) so drafts are grounded "
            "in what each organisation actually does. Re-runnable; keyed by email.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would be written without saving.")

    def handle(self, *args, **options):
        from openoutreach.signals.models import SalesLead

        written = missing = 0
        for email, (notes, why_fit) in INTEL.items():
            lead = SalesLead.objects.filter(email__iexact=email).first()
            if lead is None:
                self.stderr.write(self.style.WARNING(f"No lead with email {email!r} — skipped."))
                missing += 1
                continue
            if options["dry_run"]:
                self.stdout.write(f"WOULD WRITE #{lead.pk} {lead.organization or lead.name}")
                written += 1
                continue
            lead.notes = notes
            lead.why_fit = why_fit
            lead.save(update_fields=["notes", "why_fit", "updated_at"])
            self.stdout.write(f"#{lead.pk} {lead.organization or lead.name} — profile written")
            written += 1

        verb = "would be written" if options["dry_run"] else "written"
        self.stdout.write(self.style.SUCCESS(f"\n{written} profile(s) {verb}, {missing} lead(s) not found."))
        if not options["dry_run"] and written:
            self.stdout.write(
                "Now re-draft with --redraft so the drafts pick up the profiles:\n"
                "  python manage.py preview_cohort_drafts --followup --save --redraft --lead <id> ..."
            )
