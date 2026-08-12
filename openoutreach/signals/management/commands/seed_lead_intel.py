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
    "__DROPPED__info@wpcocala.com": (
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
    "__DROPPED__info@floridadiabetescamp.org": (
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
    "__DROPPED__rdwray@harvestinternational.org": (
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

    # ── Orange County, first touch ───────────────────────────────────────────
    # Screened from 144 in-band candidates down to 16 researched, then to these 10.
    #
    # SIX of the sixteen turned out to be existing WARM leads, caught by the
    # name-collision guard in promote_market_batch rather than by anything visible in
    # the IRS data: Grace Medical Home (Nirvana Muniz), Foundation for Foster Children
    # (Madelyn Liptak), Lighthouse Central Florida (Jarrod Daab), Mental Health
    # Association of Central Florida, Peer Support Space, and Lift Orlando. Three of
    # those screened STRONG and would otherwise have gone out as cold email to
    # organizations Marcus already knows. That guard is worth more than it looks.
    #
    # Lift Orlando was independently a poor fit anyway — $120M raised over a decade,
    # 27 staff, an existing HUD Choice Neighborhoods grant. Well past our price point.
    "information@gooca.org": (
        "OCA — Opportunity, Community, Ability. Founded 2008. Therapy and day programming for "
        "children and adults with autism and other developmental disabilities from two Central "
        "Florida campuses: 5165 Adanson St, Orlando, and a second campus at 280 S Ronald Reagan "
        "Blvd, Longwood (Seminole County). Clinical services include Applied Behavior Analysis, "
        "early intervention, mental health counselling and social skills training. Recreation "
        "includes the Running Man Theatre Company, Special Olympics training, after-school "
        "services and school break camps. Adult services run vocational and life-skills tracks "
        "plus a companion programme. "
        "SERVES: children and adults with autism and developmental disabilities across Central "
        "Florida. School break camps ages 3–22; adult programming continues past 22. Spanish-"
        "language services available. More than 300 people a year. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. They do run After-School Services and School Break "
        "Camps, but their own programme page describes these as recreation, arts and crafts, "
        "music, dance, field trips and functional communication training — not academic tutoring "
        "or homework help. "
        "GOVERNMENT FUNDING: none named on any public source. "
        "RECENT: opened the second campus in Longwood, expanding into Seminole County. Launched a "
        "neurodivergent tennis programme with USTA Florida and Seminole County (March 2026). "
        "Named primary charitable beneficiary of Visit Orlando's Magical Dining 2026.",

        "Strong fit. A roughly $3M direct-service provider actively expanding into a second "
        "county, with no visible grants staff and no named government funding anywhere public. "
        "The new Seminole footprint alongside the Orange base means two county funding "
        "landscapes to navigate at once — a concrete reason the map matters now.",
    ),
    "info@helponeheart.org": (
        "One Heart for Women and Children. Runs a community food pantry at 2040 N Rio Grande Ave, "
        "Orlando, plus monthly mobile food distributions across Orange County, a donation drop-off "
        "centre taking clothing, furniture, baby formula and diapers, and a Saturday thrift store. "
        "It is Second Harvest Food Bank's largest distribution partner and, by its own account, "
        "Orange County's largest food pantry by meals distributed. "
        "SERVES: describes itself as an 'equal-serve' pantry — children, women, men and seniors "
        "facing food insecurity, no age restriction stated. "
        "SCALE: roughly 2.6 million pounds of food (2.2 million meals) a year; over 20,000 clients "
        "a month, up from 3,000 pre-COVID; 11.5 million meals cumulatively as of January 2025. "
        "Founder Stephanie Bowman is President. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. "
        "GOVERNMENT FUNDING: none found. "
        "RECENT: relaunched on the helponeheart.org domain; 1,505 Thanksgiving baskets packed "
        "November 2025. "
        "DO NOT MENTION: the founder's personal history of domestic violence, addiction, "
        "homelessness or losing custody of her children. She tells it publicly, but it is "
        "intrusive coming from a stranger in a cold email.",

        "Strong fit, and the gap is the pitch: they move enormous volume — 20,000 clients a month "
        "— on a roughly $1M budget with no visible government funding and no evident grants "
        "function. Food security is well covered by Florida state, county and city sources that "
        "never surface on the federal databases.",
    ),
    "info@thefainehouse.org": (
        "The Faine House. Operates a 7,000 sq ft residential home at 5616 Clarcona Ocoee Rd in the "
        "Pine Hills area of Orlando, with 10 private bedroom suites for young adults aging out of "
        "foster care or on the verge of homelessness. Residents move through the RISE Programme "
        "(Resilience, Independence & Sustainable Empowerment), which requires enrolment in "
        "education or workforce training plus active employment, and adds financial literacy, life "
        "skills, mentorship and transportation support. Co-founded by retired NFL center Jeff "
        "Faine and financial executive Jeff D. Sharon; operating 11+ years. "
        "SERVES: young adults ages 18–23 who have experienced foster care or unstable housing. Not "
        "children — the population begins at 18. "
        "SCALE: 10 residents at a time; 50 young adults over four years; average stay 16 months. "
        "Very small staff — their staff page lists one named person, Director Ray Gaines. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — the entire population is 18–23. "
        "GOVERNMENT FUNDING: none found. "
        "RECENT: announced Close to Home, a purpose-built next-step residential community, with a "
        "$1M private donor pledge and a capital campaign launching in 2026. Conversations underway "
        "with Orange County about a three-acre parcel next to the existing campus — a land "
        "discussion, not confirmed funding.",

        "Strong fit and well-timed. A capital campaign launching this year plus an active Orange "
        "County land negotiation makes county and city funding immediately relevant to them, and "
        "transition-age foster youth housing is heavily funded at state and county level in ways "
        "that do not appear federally. Very small team, no sign of a grants function.",
    ),
    "info@thelifeboatproject.org": (
        "The Lifeboat Project. Long-term, trauma-informed, housing-first aftercare for adult "
        "survivors of human trafficking. The core service is the Compass Programme, a three-phase "
        "continuum ('Safe, Heal, Grow') with a minimum one-year stay, plus a transitional home for "
        "respite and Haven Homes where residents live with trained host families. Also runs "
        "community awareness work under 'Spot It. Stop It.' Founded 2011; Jill Bolander Cohen is "
        "Founder/CEO. Note: thelifeboatproject.org redirects to lifeboatproject.org. "
        "SERVES: adult survivors of human trafficking, 18 and older, regardless of gender, faith, "
        "race, sexual orientation or socioeconomic status. Also mothers with children. "
        "SCALE: about 5 employees. Budget and annual number served not published. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — adults only. "
        "GOVERNMENT FUNDING: none named on their site or LinkedIn. "
        "RECENT: sixth annual Making Waves Breakfast Benefit, March 2026, 100+ attendees. "
        "DO NOT MENTION: a February 2023 WFTV investigation in which survivors raised concerns "
        "about programming and fundraising practices. Outside the current window and damaging.",

        "Strong fit. A Florida-only direct provider with roughly five staff and no visible grants "
        "function — $150/month is priced for an organisation this size, and anti-trafficking work "
        "draws real state and county money that is not posted federally.",
    ),
    "info@samaritanvillage.net": (
        "Samaritan Village. Runs a three-stage residential Transitional Safehouse Programme in "
        "Orlando for adult women who survived sex trafficking, combining housing with therapy, "
        "addiction recovery, medical and dental care, and life-skills and financial training. "
        "Three homes, 15 beds total; stays run 12 months to 2 years per stage. Headquartered at a "
        "resale boutique whose revenue supports the transition home and provides job training for "
        "residents. Executive Director Danielle Pierson. "
        "NAMED STAGES: The Ellen Arnold Safe Home (stage 1, 6 beds, 24/7 support), The Well "
        "(stage 2, 6 beds), En-Gedi (stage 3, 3 beds, independent living). Also SOAR and the Safe "
        "Harbor Community Programme. "
        "SERVES: adult women 18+ who survived sexual exploitation and trafficking. No youth work. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. "
        "GOVERNMENT FUNDING: none named. Context, not their funding: Orange County commissioners "
        "voted in March 2026 to begin negotiating a $3.75M five-year trafficking shelter contract "
        "with a different provider, Aspire Health Partners — which shows local government money is "
        "actively moving in their service area. "
        "DO NOT MENTION: FY2023 expenses exceeding revenue, or the drop in referral calls from 419 "
        "in 2023 to 151 in 2024. Also ignore the '$12 million revenue' figure on data-broker sites "
        "— it contradicts the IRS record and is almost certainly wrong.",

        "Strong fit. A single-site Orlando provider with no visible government funding and no "
        "grants department, in a service area where county money is demonstrably in motion. A "
        "15-year provider watching a large county contract go elsewhere has an obvious reason to "
        "want the full picture — but do not say that to them.",
    ),
    "info@dsacf.org": (
        "Down Syndrome Association of Central Florida (legal name Central Florida Down Syndrome "
        "Association). Life-stage programming and family support for people with Down syndrome, "
        "organised into six tracks from prenatal through adulthood plus caregivers. Concrete "
        "offerings include Buddy Up Tennis (weekly 90-minute clinics at USTA Lake Nona with "
        "one-to-one volunteer buddies), UpBeat musical theatre run with CFCArts, and an "
        "Entrepreneur Academy training adults to start businesses. Facility at 204 N Wymore Rd, "
        "Winter Park. Awards scholarships through the DSACF Family Fund. "
        "SERVES: people with Down syndrome prenatal through adulthood, plus families and carers. "
        "Tracks: Pregnancy, Birth–Pre-K (0–4), K–Grade 8 (5–14), Teens (15–19), Adults (20+), "
        "Caregivers. About 200+ families a year, 50+ programmes and events, $30K in scholarships. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO. There is an old 'Summer Learning Academy K-5' page "
        "describing a five-week academic summer programme, but it carries no year, sits alongside "
        "a 'Summer Camps 2022' page, and the current K–Grade 8 page lists only Buddy Up Tennis and "
        "UpBeat. Treat it as legacy content — DO NOT REFERENCE IT. "
        "GOVERNMENT FUNDING: none found. Only named external grant is private and from 2017. "
        "RECENT: 27th Annual Step Up for Down Syndrome Walk, 22 August 2026, Lake Eola Park.",

        "Strong fit. An independent county association — not a chapter with funding handled "
        "nationally — small enough to have no grants team, with no government funding showing at "
        "all, so state, county and city sources would be entirely net-new to them.",
    ),
    "hello@risecs.org": (
        "IMPORTANT NAMING: the IRS record says 'Embrace Families Solutions Inc' but they separated "
        "from the Embrace Families umbrella and renamed to RISE Community Solutions in February "
        "2024. ADDRESS THEM AS RISE COMMUNITY SOLUTIONS. A separate, still-active organisation "
        "called Embrace Families exists at embracefamilies.org — do not conflate them. "
        "Five programme lines across Central Florida: the Children's Advocacy Center Osceola, a "
        "physical CAC serving child victims of sexual abuse (3,500+ children since 2014); Pathways "
        "to Home for families with children and young adults experiencing homelessness (1,200+ "
        "families since 2010); Breakthrough, a peer-support model connecting youth in mental or "
        "behavioural health crisis to therapeutic resources within seven days; Public Allies "
        "Central Florida with AmeriCorps; and Community Education. "
        "SERVES: families and youth in Central Florida. Breakthrough serves families with children "
        "9–17 including youth who have been Baker Acted. About 30 employees. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — the youth work is clinical/therapeutic and "
        "forensic/advocacy, not academic enrichment. "
        "GOVERNMENT FUNDING: CAC Osceola names the City of St. Cloud, Osceola County Government, "
        "the Florida Network of Children's Advocacy Centers and the Florida Attorney General's "
        "Office among its supporters. Public Allies runs with AmeriCorps. "
        "RECENT: Breakthrough expanded from Orange into Osceola County on an AdventHealth Central "
        "Florida Community Impact Grant, citing 90% of enrolled Orange County youth avoiding "
        "repeat psychiatric hospitalisation. "
        "DO NOT MENTION: the 2024 separation from the Embrace Families umbrella. They announced it "
        "themselves, but calling it a split or spinoff in a cold email reads as intrusive.",

        "Strong fit. They already draw precisely the money Atlas maps — City of St. Cloud, Osceola "
        "County and the Florida Attorney General are named on their own site — which means they "
        "know these sources exist and are finding them by hand. Five programme lines on 30 staff "
        "with no dedicated grants team is exactly the squeeze the product answers.",
    ),
        "askjp@jobspartnership.org": (
        "Jobs Partnership of Florida. Runs LifeWorks, a free 8-week workforce training course "
        "meeting once weekly for three hours, held at neighbourhood centres, churches, schools and "
        "businesses rather than a single campus. Curriculum bundles career planning, resume "
        "review, mock interviews, volunteer coaching and connections to employer partners in "
        "healthcare, hospitality and skilled manufacturing. Founded 1999. President/CEO Marc "
        "Stanakis. "
        "SERVES: unemployed and underemployed adults in Central Florida. Participants must be 18+ "
        "or a graduating high school senior, with a diploma or GED, stable housing, transport, "
        "work authorisation and English proficiency. "
        "SCALE: 268 participants and 216 graduates in FY2024–25, with 70% securing employment or "
        "enrolling in career/technical education. Over 3,000 people since 1999. 11 staff plus the "
        "president. More than 10,000 volunteer hours a year. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — the only K-12 touchpoint is that graduating seniors "
        "may join the adult class. Career readiness, not academic enrichment. "
        "GOVERNMENT FUNDING: none found. Their materials credit 'business, church and individual "
        "supporters'. They appear in the City of Orlando's homelessness provider directory, but "
        "that is a referral listing, not funding. "
        "RECENT: launched a no-cost 12-week healthcare-focused LifeWorks curriculum with "
        "AdventHealth University in February 2025, with a joint certificate. "
        "TONE NOTE, not a thing to avoid: the curriculum is explicitly biblically based and "
        "delivered through a church network. Purely secular framing will land flat.",

        "Strong fit, and arguably the clearest funding gap on the list: they run workforce "
        "training — the category where Florida state, CareerSource-region, county and municipal "
        "dollars are most available and least discoverable federally — on a roughly $2.3M budget "
        "with about a dozen programme staff and no visible government funding at all.",
    ),
    "info@flsteps.org": (
        "Specialized Treatment, Education and Prevention Services (STEPS). Founded 1983. "
        "Community-based substance use treatment: outpatient, intensive outpatient, day treatment, "
        "and Level II/Level IV women's residential therapeutic community care, with co-occurring "
        "mental health support. Runs a treatment programme inside the Orange County Jail, a Mobile "
        "Treatment Unit, medication assisted treatment, and HIV/STI testing. In the women's "
        "residential programme an infant or small child can live with the mother during treatment, "
        "including a child born while she is in the programme. "
        "NAMED PROGRAMS: Adult Outpatient, Adult Intensive Outpatient, Day Treatment, Women's "
        "Residential, Opioid Use Disorder, Rapid Evaluation and Appropriate Placement (REAP), "
        "Orange County Jail Inmate Treatment, Medication Assisted Treatment, Mobile Treatment Unit, "
        "The Living Room (24/7), Care Coordination, Comprehensive Needs of Fathers. "
        "SERVES: adults with substance use and co-occurring disorders, with stated priority "
        "admission for people who are indigent, pregnant, postpartum, parenting, or injecting drug "
        "users. Also Orange County Jail inmates. Service area Orange, Seminole and Brevard. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — all clinical treatment for adults. "
        "GOVERNMENT FUNDING: named on their own site — programmes are sponsored by Central Florida "
        "Cares Health System (the regional managing entity) and the Florida Department of Children "
        "and Families. The jail programme ties to the Edward Byrne Memorial Justice Assistance "
        "Grant. "
        "SCALE: not published on their own site — do not cite a staff count or budget.",

        "Moderate fit. They already sit inside the DCF / Central Florida Cares managing-entity "
        "pipeline, so the state behavioural-health channel is familiar and the standard 'state "
        "money you cannot see' line will underwhelm them. The real angle is the layer outside that "
        "pipeline — Orange County health and justice-diversion dollars, City of Orlando funds — "
        "because their funding looks concentrated in a single channel.",
    ),
    "marketing@victimservicecenter.org": (
        "Victim Service Center of Central Florida. The Certified Rape Crisis Center for Orange, "
        "Osceola and Seminole counties, providing free crisis intervention, individual and group "
        "therapy, victim advocacy and forensic exams to survivors of sexual assault and violent "
        "crime. Runs a 24/7 helpline and maintains a confidential forensic evidence collection "
        "location separate from its main office at 2111 East Michigan Street, Suite 210, Orlando. "
        "Delivers prevention education and professional training to schools, first responders, "
        "workplaces and organisations. "
        "NAMED PROGRAMS: Crisis Intervention and Helpline (24/7), Individual and Group Therapy, "
        "Forensic Exams, Victim Advocacy, Prevention Education and Training, Community Outreach, "
        "Emotions in Motion (with Orlando Ballet). "
        "SERVES: victims of sexual assault, violent crime and traumatic circumstances in Orange, "
        "Osceola and Seminole counties. Prevention programming reaches K through college, plus "
        "populations they name as LGBTQ, Spanish-speaking and homeless individuals. "
        "OUT-OF-SCHOOL-TIME PROGRAMMING: NO — the K-through-college prevention education is "
        "violence-prevention curriculum delivered into schools and community settings, not "
        "after-school or summer academic enrichment. "
        "GOVERNMENT FUNDING: named on their own site — 'Award No. VOCA-C-2025-Victim Service "
        "Center of Central-00090 & 00161 awarded by the Office for Victims of Crime.' Certified "
        "Rape Crisis Center status ties them to the Florida Attorney General and the Florida "
        "Council Against Sexual Violence funding structures. "
        "SCALE: their homepage impact counters render as zeros — no figures available. Do not cite "
        "a number served. "
        "DO NOT MENTION: the executive director transition. Address the organisation, never a "
        "named director. Also do not reference their homepage statistics.",

        "Moderate fit, and the weakest timing of the twenty: a new Executive Director arrived in "
        "May 2026, which makes a near-term vendor decision unlikely until she settles in. They are "
        "also already deep in the state VOCA / Attorney General channel. Worth a first touch "
        "because they are Florida-only, not a funder and not a national chapter — but expect this "
        "one to need a second touch months out rather than converting now.",
    ),
}


# Leads removed from the send list, and why. Their researched profiles are kept above
# (under a __DROPPED__ key) rather than deleted, because the profile IS the evidence for
# the decision — without it, someone re-promotes the same org in three months.
#
# Marking them PASSED rather than deleting them means preview_cohort_drafts skips them
# (it already excludes PASSED) and they cannot drift back into a batch.
DROPPED: dict[str, str] = {
    "rdwray@harvestinternational.org":
        "Delivers no programmes in Florida — a Florida-headquartered international missions "
        "org whose work is in Cuba, Haiti, India, Kenya, Romania, Uganda, Ukraine and Zimbabwe. "
        "Atlas maps Florida state and county funding. There is no honest pitch here.",
    "info@wpcocala.com":
        "97.6% of revenue is private contributions and no government funding could be found. "
        "The state/county funding gap is the wrong pitch for them, and this is the lead where "
        "the false 'already earmarked' claim appeared twice.",
    "info@floridadiabetescamp.org":
        "States on their own About page that the organisation 'does not receive any governmental "
        "money'. Leading with the state-and-county funding gap tells them we did not read "
        "their site.",
}


class Command(BaseCommand):
    help = ("Write researched profiles onto cold leads (notes + why_fit) so drafts are grounded "
            "in what each organisation actually does, and mark screened-out leads as passed. "
            "Re-runnable; keyed by email.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would change without saving.")

    def handle(self, *args, **options):
        from openoutreach.signals.models import DispositionReason, SalesLead

        dry = options["dry_run"]
        written = dropped = missing = 0

        for email, (notes, why_fit) in INTEL.items():
            if email.startswith("__DROPPED__"):
                continue  # profile retained as evidence; the lead is handled via DROPPED below
            lead = SalesLead.objects.filter(email__iexact=email).first()
            if lead is None:
                self.stderr.write(self.style.WARNING(f"No lead with email {email!r} — skipped."))
                missing += 1
                continue
            if not dry:
                # research_profile, not notes: notes is the legacy mixed field and is
                # no longer trusted as writer evidence.
                lead.research_profile = notes
                lead.why_fit = why_fit
                lead.save(update_fields=["research_profile", "why_fit", "updated_at"])
            self.stdout.write(f"{'WOULD WRITE' if dry else 'profile written'} "
                              f"#{lead.pk} {lead.organization or lead.name}")
            written += 1

        for email, reason in DROPPED.items():
            lead = SalesLead.objects.filter(email__iexact=email).first()
            if lead is None:
                self.stderr.write(self.style.WARNING(f"No lead with email {email!r} — nothing to drop."))
                missing += 1
                continue
            if not dry:
                # Structured disposition, not a status flag plus a prose note. The
                # reason code is queryable, the gate in send_outreach_email reads it,
                # and the draft is preserved rather than wiped — history is not rewritten
                # because a later decision went the other way.
                lead.set_disposition(
                    DispositionReason.OUTSIDE_CAMPAIGN_CRITERIA,
                    detail=reason, source="human")
                lead.status = SalesLead.Status.PASSED
                lead.save(update_fields=[
                    "status", "disposition", "disposition_reason", "disposition_detail",
                    "disposition_scope", "disposition_source", "disposition_at", "updated_at"])
            self.stdout.write(self.style.WARNING(
                f"{'WOULD DROP' if dry else 'dropped'} #{lead.pk} {lead.organization or lead.name} — {reason[:70]}…"))
            dropped += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{written} profile(s), {dropped} lead(s) removed from the send list, "
            f"{missing} not found."))
        if not dry and written:
            self.stdout.write(
                "Now re-draft with --redraft so drafts pick up the profiles:\n"
                "  python manage.py preview_cohort_drafts --followup --save --redraft"
            )
