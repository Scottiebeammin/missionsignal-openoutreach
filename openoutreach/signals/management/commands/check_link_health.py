"""Link-health check for the resource/funder/opportunity directory.

Probes every active ResourceProvider and Funder website (plus Opportunity
source_urls) with an 8s HEAD-then-GET. 403s are treated as OK (bot blocks).
Only DNS/connection failures deactivate a row; HTTP 404s are logged for
human review, never auto-deactivated. Prints a summary.
"""

import socket
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from openoutreach.funding.models import Funder, Opportunity, ResourceProvider

TIMEOUT = 8
OK_STATUSES = set(range(200, 400)) | {401, 403, 405, 406, 429}  # bot-blocks/auth walls = alive
UA = "Mozilla/5.0 (compatible; AnansiAtlasLinkCheck/1.0)"


def probe(url):
    """Return ('ok', status) | ('http_error', status) | ('dns_dead', reason) | ('unreachable', reason).

    Only 'dns_dead' (the domain no longer resolves) triggers deactivation.
    Timeouts, TLS problems, and connection resets are transient/ambiguous — flag only.
    """
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return ("ok", resp.status)
        except urllib.error.HTTPError as exc:
            if exc.code in OK_STATUSES:
                return ("ok", exc.code)
            if method == "GET":
                return ("http_error", exc.code)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.gaierror):
                return ("dns_dead", str(exc.reason))
            if method == "GET":
                return ("unreachable", str(exc.reason))
        except socket.gaierror as exc:
            return ("dns_dead", str(exc))
        except Exception as exc:  # timeout, bad handshake, reset — ambiguous, flag only
            if method == "GET":
                return ("unreachable", str(exc))
    return ("unreachable", "unreachable")


class Command(BaseCommand):
    help = "Check every active resource/funder/opportunity URL; deactivate DNS-dead rows, log 404s."

    def handle(self, *args, **options):
        checked = ok = http_errors = unreachable = dns_dead = deactivated = 0

        def check_row(label, row, url, can_deactivate):
            nonlocal checked, ok, http_errors, unreachable, dns_dead, deactivated
            checked += 1
            status, detail = probe(url)
            if status == "ok":
                ok += 1
                return
            if status == "http_error":
                http_errors += 1
                self.stdout.write(self.style.WARNING(f"HTTP {detail}: {label} '{row}' {url} (flagged, not deactivated)"))
                return
            if status == "unreachable":
                unreachable += 1
                self.stdout.write(self.style.WARNING(f"UNREACHABLE ({detail}): {label} '{row}' {url} (flagged, not deactivated)"))
                return
            dns_dead += 1
            self.stdout.write(self.style.ERROR(f"DNS DEAD ({detail}): {label} '{row}' {url}"))
            if can_deactivate:
                row.active = False
                row.save(update_fields=["active", "updated_at"])
                deactivated += 1
                self.stdout.write(f"  -> deactivated {label} '{row}'")

        for r in ResourceProvider.objects.filter(active=True).exclude(website=""):
            if "example." in r.website:
                continue  # demo rows
            check_row("ResourceProvider", r, r.website, can_deactivate=True)

        for f in Funder.objects.filter(active=True).exclude(website=""):
            if "example." in f.website:
                continue
            check_row("Funder", f, f.website, can_deactivate=True)

        for o in Opportunity.objects.filter(status=Opportunity.Status.ACTIVE):
            for url in (o.source_urls or []):
                if not isinstance(url, str) or not url.startswith("http") or "example." in url:
                    continue
                # Opportunities have no simple active bool semantics for links; flag only.
                check_row("Opportunity", o, url, can_deactivate=False)

        self.stdout.write(self.style.SUCCESS(
            f"Link health: checked={checked} ok={ok} http_errors={http_errors} "
            f"unreachable={unreachable} dns_dead={dns_dead} deactivated={deactivated}"
        ))
