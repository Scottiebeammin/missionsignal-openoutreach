#!/usr/bin/env python
"""
Recapture the vision-film screenshots at 2x DPR.

Why: the original shots are 1600x1000 CSS pixels at 1x, which go soft under the
film's slow 16:9 push-and-hold. Playwright's device_scale_factor=2 gives a
3200x2000 image from the SAME 1600x1000 layout, so nothing about the composition
or the ScreenshotPanel geometry changes — only the pixel density. Keep the
viewport 16:10; the panel components assume that aspect.

TWO THINGS THIS SCRIPT EXISTS TO GET RIGHT
------------------------------------------
1. The onboarding tour. Every client page opens with a "STEP 1 OF 8 — Start at
   Home" modal over a dimming backdrop. A naive capture screenshots the modal,
   not the product. We click #tour-skip and wait for .tour-overlay to detach.

2. Sc12's A/B pair. The Foundations page has a real sort toggle
   (openoutreach/signals/foundations.py): `sort=fit` (default) ranks the 990-PF
   grant receipts by proximity to the org's budget_target_amount -> peer-size
   grants; `sort=largest` puts the biggest gifts first. The difference is in the
   receipts table LOW on the page, not in the foundation cards up top — so both
   shots must be scrolled to that table, at the SAME pixel offset, or the wipe
   in Sc12 reveals nothing. We scroll the first shot into view, record
   window.scrollY, and replay that exact offset for the second.

Verified against real data (project 14): sort=largest tops out with the Leona M
and Harry B Helmsley Charitable Trust; sort=fit tops out with $25,000 grants to
Orange County orgs (Apopka Serves, Frontline Outreach, Lake Nona Institute).
That is exactly what the Sc12 narration claims.

Usage (dev server must already be running):
  python scripts/capture-hd-shots.py --session <sessionid> [--project 14] [--port 8731]

Project 14 = Empowered Girls Inc., the real founding partner; Scott authorised
using their data on screen (2026-07-29), which makes the film coherent — the org
named in Act V is the org shown in Act III. Project 13 (Horizon Youth Collective)
is the seeded demo persona, if a non-client capture is ever needed instead.
"""
import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1600, "height": 1000}  # 16:10 — matches the existing shot set
DPR = 2
# Nudge past the receipts table header so the grant rows fill the frame.
SCROLL_EXTRA = 300


def dismiss_tour(page) -> bool:
    """Click through the onboarding modal. Returns True if a tour was present."""
    try:
        btn = page.locator("#tour-skip")
        if btn.count() and btn.first.is_visible():
            btn.first.click()
            page.wait_for_selector(".tour-overlay", state="detached", timeout=5_000)
            page.wait_for_timeout(250)
            return True
    except Exception:
        # A page with no tour, or one that already dismissed it, is fine.
        pass
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="Django sessionid cookie value")
    ap.add_argument("--project", type=int, default=14)
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--outdir", default="public/screenshots")
    # Per-prospect shot sets live side by side: `hd-` is the vision film (project 14),
    # `bam-` is the BAM Orlando board film (project 18). Same geometry, same script.
    ap.add_argument("--prefix", default="hd-")
    # Cosmetic, capture-time only — never a change to the product.
    #
    # A film pitched AT a prospect renders that prospect's workspace, and some of
    # what the app shows is true for a signed partner but not for a prospect. The
    # founding-partner badge is honest on project 14 (Empowered Girls really is
    # partner #1) and presumptuous on project 18 (BAM has not signed). Same for a
    # zero-valued stat: "0 verified grants matched to you" is accurate and useless
    # on a workspace whose analysis has never run, and it undercuts a slide whose
    # whole job is to show potential.
    #
    # So the decision lives with the shot, not the template:
    #   --hide ".fw-badge,.fw-sub,.fw-stat-verified"
    ap.add_argument("--hide", default="", help="Comma-separated CSS selectors to hide before capture")
    ap.add_argument("--only", default="", help="Comma-separated shot names (sans prefix) to re-capture")
    args = ap.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    p = f"/projects/{args.project}"
    out = pathlib.Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    # (name, path, scroll_to_text) — scroll_to_text anchors the Sc12 pair on the
    # receipts table. None means "top of page".
    q = args.prefix
    plan = [
        (f"{q}dashboard",     f"{p}/dashboard/",                    None),
        (f"{q}web",           f"{p}/web/",                          None),
        # Anchor on the receipts TABLE HEADER, not the toggle: the toggle sits at the
        # panel top and leaves the grant rows below the fold, and those rows ARE the
        # reveal. +EXTRA nudges the header up so header + several rows fill the frame.
        (f"{q}opps-default",  f"{p}/foundations/?sort=largest",     "Gave To"),
        (f"{q}opps-peersize", f"{p}/foundations/",                  "Gave To"),
        (f"{q}readiness",     f"{p}/readiness/",                    None),
        (f"{q}ecosystem",     f"{p}/ecosystem/",                    None),
    ]

    if args.only:
        wanted = {f"{q}{n.strip()}" for n in args.only.split(",") if n.strip()}
        plan = [row for row in plan if row[0] in wanted]
        if not plan:
            print(f"--only matched no shots. Available: {', '.join(n for n, _, _ in plan)}")
            return 1

    hide = [s.strip() for s in args.hide.split(",") if s.strip()]

    failures = []
    locked_scroll = None  # reused so the Sc12 pair frames identically

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=DPR)
        ctx.add_cookies([{
            "name": "sessionid", "value": args.session,
            "domain": "127.0.0.1", "path": "/",
        }])
        page = ctx.new_page()

        for name, path, anchor in plan:
            url = base + path
            resp = page.goto(url, wait_until="networkidle", timeout=60_000)
            code = resp.status if resp else 0

            # A login redirect would otherwise yield six screenshots of the sign-in page.
            if "/accounts/login" in page.url:
                failures.append(f"{name}: redirected to login (bad session)")
                print(f"  x {name:20s} HTTP {code} -> LOGIN REDIRECT")
                continue
            if code >= 400:
                failures.append(f"{name}: HTTP {code}")
                print(f"  x {name:20s} HTTP {code}")
                continue

            had_tour = dismiss_tour(page)

            # Hide AFTER the tour clears (the tour overlay can re-layout the page)
            # and BEFORE any scroll anchoring, so the locked scrollY is measured
            # against the same layout the screenshot will show.
            hidden = 0
            if hide:
                for sel in hide:
                    try:
                        hidden += page.locator(sel).count()
                    except Exception:
                        pass
                page.add_style_tag(content=" ".join(f"{sel}{{display:none!important}}" for sel in hide))
                page.wait_for_timeout(250)

            note = ""
            if anchor:
                if locked_scroll is None:
                    page.get_by_text(anchor, exact=False).first.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    page.evaluate(f"window.scrollBy(0, {SCROLL_EXTRA})")
                    page.wait_for_timeout(400)
                    locked_scroll = page.evaluate("window.scrollY")
                    note = f" scrollY={locked_scroll} (locked)"
                else:
                    page.evaluate(f"window.scrollTo(0, {locked_scroll})")
                    page.wait_for_timeout(400)
                    note = f" scrollY={locked_scroll} (replayed)"

            page.wait_for_timeout(900)  # let fonts/animation settle
            dest = out / f"{name}.png"
            page.screenshot(path=str(dest))
            print(f"  ok {name:20s} HTTP {code}  {dest.stat().st_size/1024:.0f} KB"
                  f"{'  tour-dismissed' if had_tour else ''}"
                  f"{f'  hid {hidden} el' if hide else ''}{note}")
            # A --hide that matched nothing is almost always a stale selector, and it
            # fails silently into a screenshot that still shows what you meant to drop.
            if hide and hidden == 0:
                failures.append(f"{name}: --hide matched 0 elements ({args.hide})")

        # Guard: if the Sc12 pair came out byte-identical the wipe reveals nothing.
        a, b = out / f"{q}opps-default.png", out / f"{q}opps-peersize.png"
        if a.exists() and b.exists() and a.read_bytes() == b.read_bytes():
            failures.append("Sc12 pair is byte-identical — the sort toggle changed nothing")

        browser.close()

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("\nall shots captured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
