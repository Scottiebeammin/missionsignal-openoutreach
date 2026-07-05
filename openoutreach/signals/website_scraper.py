"""Lightweight website text extraction — no Playwright, no JS rendering.

Fetches the homepage (or a given URL) over HTTP and returns clean body text
suitable for passing into the deterministic analyzer.  Silently returns an
empty string on any error so the intake flow is never blocked.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

import httpx


_TIMEOUT = 10  # seconds
_MAX_BYTES = 256_000  # ~256 KB — enough for any homepage

# Internal pages worth pulling for verification — where orgs actually list
# their programs and who they serve.
_SUBPAGE_HINTS = (
    "about", "program", "what-we-do", "services", "our-work", "mission",
    "who-we-serve", "impact", "initiatives",
)


def _strip_tags(html: str) -> str:
    """Remove HTML/script/style content and return plain text."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&[a-z]+;", " ", html)
    html = re.sub(r"\s{2,}", " ", html)
    return html.strip()


def scrape_website_text(url: str, *, max_chars: int = 8_000) -> str:
    """Return cleaned text from the website homepage. Returns '' on failure."""
    if not url or not url.startswith(("http://", "https://")):
        url = f"https://{url}" if url else ""
    if not url:
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AnansiAtlasBot/1.0; "
                "+https://anansi-atlas.com)"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            content = response.text[:_MAX_BYTES]
        return _strip_tags(content)[:max_chars]  # analyzer default 8k; verification scans deeper
    except Exception:
        return ""


def _normalize_url(url: str) -> str:
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url or ""


def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (compatible; AnansiAtlasBot/1.0; +https://anansi-atlas.com)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }


def scrape_site_text(url: str, *, max_pages: int = 4, max_chars: int = 40_000) -> str:
    """Homepage + a few same-host about/program pages, concatenated.

    Multi-page so verification checks a program listed on /programs, not just
    the homepage. Same-host only, best-effort: any fetch failure is skipped and
    partial text is still returned. Falls back to homepage-only text if no
    relevant subpages are linked.
    """
    url = _normalize_url(url)
    if not url:
        return ""
    home_host = urlsplit(url).netloc
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers=_headers()) as client:
            home = client.get(url)
            home.raise_for_status()
            home_html = home.text[:_MAX_BYTES]
            texts = [_strip_tags(home_html)]

            # Discover same-host subpages whose href/anchor hints at about/programs.
            links = re.findall(r'href=["\']([^"\'#]+)["\']', home_html, flags=re.I)
            seen, picked = {url.rstrip("/")}, []
            for href in links:
                absolute = urljoin(url, href.strip())
                if urlsplit(absolute).netloc != home_host:
                    continue
                key = absolute.rstrip("/")
                if key in seen:
                    continue
                if any(hint in absolute.casefold() for hint in _SUBPAGE_HINTS):
                    seen.add(key)
                    picked.append(absolute)
                if len(picked) >= max_pages - 1:
                    break

            for sub in picked:
                try:
                    resp = client.get(sub)
                    resp.raise_for_status()
                    texts.append(_strip_tags(resp.text[:_MAX_BYTES]))
                except Exception:
                    continue
    except Exception:
        return scrape_website_text(url, max_chars=max_chars)
    return " ".join(texts)[:max_chars]
