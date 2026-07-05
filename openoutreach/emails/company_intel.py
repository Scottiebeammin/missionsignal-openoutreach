# openoutreach/emails/company_intel.py
"""Firmographic company intelligence from a public company website.

A best-effort, stdlib-only web analyzer: given a company domain it fetches the
homepage plus a few well-known subpages and extracts firmographics — industry
signals, tech stack, social profiles, size/funding signals, hiring status, and
any team members / contact details exposed in the markup.

This is the deterministic half of the "AI sales team" research workflow, ported
into the backend so the qualifier can enrich a Deal automatically at the
QUALIFIED gate (see ``Lead.resolve_company_intel``). It sits alongside the email
finder (``finder.py``) as the second external-enrichment provider: the finder
resolves *who* to contact, this resolves *what the company is*.

Design notes:
- Pure standard library (``urllib`` + ``html.parser`` + ``re``). No new deps, so
  it is safe in the slim ``web.txt`` build and never gates the daemon.
- TLS verification stays **on** (unlike the upstream skill script, which
  disabled it): we only ever scrape public marketing pages, so there is no
  reason to accept an unverified certificate.
- Every network/parse failure is swallowed and degrades to partial or empty
  data — enrichment must never crash the pipeline.
"""
from __future__ import annotations

import json
import logging
import re
import ssl
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; OpenOutreach-CompanyIntel/1.0)"
_DEFAULT_TIMEOUT = 8

# Subpages worth a look for firmographics, in priority order.
_SUBPAGES = ("/about", "/about-us", "/team", "/our-team", "/leadership",
             "/careers", "/jobs", "/contact")

# Free/personal mail providers whose domain is NOT a company website.
_FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "ymail.com", "icloud.com", "me.com", "aol.com", "proton.me",
    "protonmail.com", "gmx.com", "mail.com", "zoho.com", "yandex.com",
})

_TECH_SIGNATURES = {
    "WordPress": [r"wp-content", r"wp-includes"],
    "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme"],
    "HubSpot": [r"hs-scripts\.com", r"hbspt", r"hubspot"],
    "Webflow": [r"webflow\.com", r"Webflow"],
    "Next.js": [r"_next/static", r"__NEXT_DATA__"],
    "React": [r"react-dom", r"react\.production\.min"],
    "Vue.js": [r"vue\.min\.js", r"vue\.runtime"],
    "Angular": [r"angular\.min\.js", r"ng-version"],
    "Gatsby": [r"___gatsby", r"gatsby"],
    "Squarespace": [r"static\.squarespace", r"squarespace\.com"],
    "Wix": [r"parastorage\.com", r"wix\.com"],
    "Google Analytics": [r"google-analytics\.com", r"googletagmanager", r"gtag/js"],
    "Segment": [r"cdn\.segment\.com"],
    "Intercom": [r"widget\.intercom\.io", r"intercom"],
    "Drift": [r"js\.driftt\.com", r"drift\.com"],
    "Stripe": [r"js\.stripe\.com"],
    "Salesforce": [r"force\.com", r"salesforce"],
    "Marketo": [r"marketo", r"mktoresp"],
}

_SOCIAL_PATTERNS = {
    "linkedin": r"linkedin\.com/(?:company|in)/[\w-]+",
    "twitter": r"(?:twitter|x)\.com/[\w]+",
    "facebook": r"facebook\.com/[\w.]+",
    "instagram": r"instagram\.com/[\w.]+",
    "youtube": r"youtube\.com/(?:c/|channel/|@)[\w-]+",
    "github": r"github\.com/[\w-]+",
}

_INDUSTRY_KEYWORDS = {
    "SaaS": ["saas", "software as a service", "cloud platform", "subscription"],
    "Fintech": ["fintech", "financial technology", "payments", "banking"],
    "Healthcare": ["healthcare", "health tech", "medical", "patient", "clinical"],
    "E-commerce": ["ecommerce", "e-commerce", "online store", "retail"],
    "EdTech": ["edtech", "education", "learning platform", "courses"],
    "Cybersecurity": ["cybersecurity", "cyber", "threat", "vulnerability"],
    "AI/ML": ["artificial intelligence", "machine learning", "ai-powered", "deep learning"],
    "DevTools": ["devtools", "developer platform", "sdk", "infrastructure"],
    "MarTech": ["martech", "marketing automation", "campaign", "analytics"],
    "HRTech": ["hr tech", "human resources", "recruiting", "talent"],
    "Nonprofit": ["nonprofit", "non-profit", "501(c)(3)", "donors", "charity"],
}

_FUNDING_MARKERS = ("Series A", "Series B", "Series C", "Series D", "IPO",
                    "publicly traded", "public company")


# ---------------------------------------------------------------------------
# HTML collection
# ---------------------------------------------------------------------------

class _TagCollector(HTMLParser):
    """Minimal parser collecting title, meta, headings, scripts and JSON-LD."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.headings: list[dict[str, str]] = []
        self.scripts: list[str] = []
        self.json_ld: list = []
        self._in_title = False
        self._in_ld = False
        self._ld_buf = ""
        self._tag = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._tag = tag
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = a.get("name", a.get("property", "")).lower()
            content = a.get("content", "")
            if name and content:
                self.meta[name] = content
        elif tag == "script":
            src = a.get("src", "")
            if src:
                self.scripts.append(src)
            if "ld+json" in a.get("type", ""):
                self._in_ld = True
                self._ld_buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False
            try:
                self.json_ld.append(json.loads(self._ld_buf))
            except (json.JSONDecodeError, ValueError):
                pass
        self._tag = ""

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif self._in_ld:
            self._ld_buf += data
        elif self._tag in ("h1", "h2", "h3"):
            text = data.strip()
            if text:
                self.headings.append({"level": self._tag, "text": text})


# ---------------------------------------------------------------------------
# Network + parse
# ---------------------------------------------------------------------------

def _fetch(url: str, timeout: int = _DEFAULT_TIMEOUT) -> tuple[int | None, str | None]:
    """GET a URL. Returns (status, html) or (status_or_None, None) on failure.

    TLS verification stays on. All errors are swallowed — this is best-effort.
    """
    ctx = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, resp.read().decode(charset, errors="replace")
    except HTTPError as exc:
        return exc.code, None
    except (URLError, OSError, ValueError):
        return None, None


def _parse(html: str) -> _TagCollector:
    collector = _TagCollector()
    try:
        collector.feed(html)
    except Exception:  # noqa: BLE001 — malformed markup must not propagate
        pass
    return collector


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def _company_name(parsed: _TagCollector) -> str:
    for key in ("og:site_name", "application-name"):
        if key in parsed.meta:
            return parsed.meta[key]
    if parsed.title:
        name = re.split(r"[|\-—]", parsed.title)[0].strip()
        if name:
            return name
    for h in parsed.headings:
        if h["level"] == "h1":
            return h["text"]
    return ""


def _description(parsed: _TagCollector) -> str:
    for key in ("description", "og:description", "twitter:description"):
        if key in parsed.meta:
            return parsed.meta[key]
    return ""


def _tech_stack(html: str, parsed: _TagCollector) -> list[str]:
    combined = html + " ".join(parsed.scripts)
    detected = []
    for tech, patterns in _TECH_SIGNATURES.items():
        if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
            detected.append(tech)
    generator = parsed.meta.get("generator", "")
    if generator and generator not in detected:
        detected.append(generator)
    return sorted(set(detected))


def _social_links(html: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for platform, pattern in _SOCIAL_PATTERNS.items():
        matches = re.findall(r"https?://(?:www\.)?" + pattern, html, re.IGNORECASE)
        if matches:
            found[platform] = sorted(set(matches))[:3]
    return found


def _industry_signals(html: str) -> list[str]:
    low = html.lower()
    scores = {ind: sum(1 for kw in kws if kw in low)
              for ind, kws in _INDUSTRY_KEYWORDS.items()}
    ranked = sorted((s for s in scores.items() if s[1] > 0), key=lambda x: -x[1])
    return [ind for ind, _ in ranked[:3]]


def _size_signals(html: str) -> dict:
    signals: dict = {}
    emp = re.search(r"(\d[\d,]*)\+?\s*(?:employees?|team\s*members?|people)", html, re.IGNORECASE)
    if emp:
        signals["estimated_employees"] = emp.group(1).replace(",", "")
    for marker in _FUNDING_MARKERS:
        if marker.lower() in html.lower():
            signals["funding_stage"] = marker
            break
    return signals


def _has_job_postings(html: str) -> bool:
    indicators = (r"open\s*positions", r"job\s*openings", r"we[’'`\s]*re\s*hiring",
                  r"current\s*openings", r"view\s*all\s*jobs", r"join\s*our\s*team")
    return any(re.search(p, html, re.IGNORECASE) for p in indicators)


def _contact_info(html: str) -> dict:
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html)
    phones = re.findall(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", html)
    emails = [e for e in emails if not e.lower().endswith((".png", ".jpg", ".svg", ".gif", ".webp"))]
    return {"emails": sorted(set(emails))[:5], "phones": sorted(set(phones))[:3]}


def _team_members(html: str) -> list[dict]:
    """Team members from JSON-LD Person schemas (the reliable signal only)."""
    members: list[dict] = []
    for match in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    ):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type") == "Person" and item.get("name"):
                members.append({
                    "name": item.get("name", ""),
                    "title": item.get("jobTitle", ""),
                    "url": item.get("url", ""),
                })
    seen, unique = set(), []
    for m in members:
        key = m["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique[:20]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def intel_digest(intel: dict | None) -> str:
    """Compact plain-text digest of stored firmographics for prompt injection.

    The outreach agents (email opener, LinkedIn follow-up) receive this via
    ``base_context`` so drafts can reference something concrete about the
    company. Returns ``""`` when there is nothing usable — the prompt template
    gates the whole section on truthiness, so a lead without intel renders
    exactly the pre-intel prompt.
    """
    if not intel:
        return ""
    lines = []
    name = intel.get("company_name") or ""
    domain = intel.get("domain") or ""
    if name or domain:
        label = f"{name} ({domain})" if name and domain else (name or domain)
        lines.append(f"- Company: {label}")
    if intel.get("description"):
        lines.append(f"- What they do: {intel['description']}")
    if intel.get("industry_signals"):
        lines.append(f"- Industry: {', '.join(intel['industry_signals'])}")
    size = intel.get("company_size_signals") or {}
    size_bits = []
    if size.get("estimated_employees"):
        size_bits.append(f"~{size['estimated_employees']} employees")
    if size.get("funding_stage"):
        size_bits.append(size["funding_stage"])
    if size_bits:
        lines.append(f"- Size/funding: {', '.join(size_bits)}")
    if intel.get("has_job_postings"):
        lines.append("- Actively hiring (open roles on their careers page)")
    if intel.get("tech_stack"):
        lines.append(f"- Website tech: {', '.join(intel['tech_stack'][:6])}")
    return "\n".join(lines)


def domain_from_email(email: str | None) -> str | None:
    """Company domain from a work email, or None for personal/free-mail addresses."""
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip().lower().rstrip(".")
    if not domain or "." not in domain or domain in _FREE_EMAIL_DOMAINS:
        return None
    return domain


def analyze_company(url: str, *, timeout: int = _DEFAULT_TIMEOUT,
                    max_subpages: int = 4) -> dict | None:
    """Fetch a company site and extract firmographics.

    ``url`` may be a bare domain (``acme.com``) or a full URL. Returns a dict of
    firmographic signals, or None if the homepage could not be fetched at all.
    Never raises for network/parse failures — degrades to partial data.
    """
    if not urlparse(url).scheme:
        url = "https://" + url
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"

    status, html = _fetch(url, timeout)
    if not html:
        logger.info("company_intel: could not fetch %s (status %s)", url, status)
        return None

    home = _parse(html)
    result = {
        "domain": parts.netloc,
        "company_name": _company_name(home),
        "description": _description(home),
        "industry_signals": _industry_signals(html),
        "tech_stack": _tech_stack(html, home),
        "social_links": _social_links(html),
        "company_size_signals": _size_signals(html),
        "has_job_postings": _has_job_postings(html),
        "team_members": _team_members(html),
        "contact_info": _contact_info(html),
        "pages_analyzed": [url],
    }

    all_html = html
    for path in _SUBPAGES:
        if len(result["pages_analyzed"]) > max_subpages:
            break
        sub_url = urljoin(base, path)
        sub_status, sub_html = _fetch(sub_url, timeout)
        if sub_status != 200 or not sub_html:
            continue
        result["pages_analyzed"].append(sub_url)
        all_html += sub_html
        if any(k in path for k in ("team", "about", "leadership")):
            result["team_members"].extend(_team_members(sub_html))
        if any(k in path for k in ("career", "job")):
            result["has_job_postings"] = result["has_job_postings"] or _has_job_postings(sub_html)
        if "contact" in path:
            extra = _contact_info(sub_html)
            result["contact_info"]["emails"] = sorted(set(
                result["contact_info"]["emails"] + extra["emails"]))[:5]
            result["contact_info"]["phones"] = sorted(set(
                result["contact_info"]["phones"] + extra["phones"]))[:3]

    # Merge social links discovered on subpages, and de-dup team members.
    for platform, urls in _social_links(all_html).items():
        merged = sorted(set(result["social_links"].get(platform, []) + urls))[:3]
        result["social_links"][platform] = merged
    seen, unique = set(), []
    for m in result["team_members"]:
        key = m["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(m)
    result["team_members"] = unique[:20]

    return result
