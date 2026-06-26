"""Lightweight website text extraction — no Playwright, no JS rendering.

Fetches the homepage (or a given URL) over HTTP and returns clean body text
suitable for passing into the deterministic analyzer.  Silently returns an
empty string on any error so the intake flow is never blocked.
"""
from __future__ import annotations

import re

import httpx


_TIMEOUT = 10  # seconds
_MAX_BYTES = 256_000  # ~256 KB — enough for any homepage


def _strip_tags(html: str) -> str:
    """Remove HTML/script/style content and return plain text."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&[a-z]+;", " ", html)
    html = re.sub(r"\s{2,}", " ", html)
    return html.strip()


def scrape_website_text(url: str) -> str:
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
        return _strip_tags(content)[:8_000]  # cap at 8k chars for the analyzer
    except Exception:
        return ""
