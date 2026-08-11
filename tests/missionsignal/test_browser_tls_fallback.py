"""fldoe.org permits crawling in robots.txt but its Akamai edge refuses any client
whose TLS handshake isn't a browser's — a full Chrome header set is still 403, so
it was never a User-Agent problem. web_discovery retries a 403 once with a browser
TLS fingerprint rather than shipping Chromium in the web image.

The rules that matter: the retry fires ONLY on 403, it keeps the same-host redirect
promise the stdlib path makes, and it fails closed when the optional dependency is
missing.
"""
import urllib.error
from unittest import mock

import pytest

from openoutreach.funding import web_discovery


def _http_error(code):
    return urllib.error.HTTPError("https://example.gov/x", code, "nope", None, None)


def test_a_200_never_reaches_the_fallback():
    with mock.patch.object(web_discovery, "_browser_tls_get") as fallback:
        opener = mock.MagicMock()
        resp = opener.open.return_value.__enter__.return_value
        resp.headers.get.return_value = "text/html"
        resp.headers.get_content_charset.return_value = "utf-8"
        resp.read.return_value = b"<html>ok</html>"
        with mock.patch.object(web_discovery.urllib.request, "build_opener", return_value=opener):
            body, _, _ = web_discovery._http_get("https://example.gov/x", 10, 1000)
    assert body == b"<html>ok</html>"
    fallback.assert_not_called()


@pytest.mark.parametrize("code", [404, 500, 503, 401])
def test_only_403_is_retried(code):
    """A 404 is a real answer. Retrying every failure with a browser fingerprint
    would be pointless traffic against sites that simply do not have the page."""
    with mock.patch.object(web_discovery, "_browser_tls_get") as fallback:
        opener = mock.MagicMock()
        opener.open.side_effect = _http_error(code)
        with mock.patch.object(web_discovery.urllib.request, "build_opener", return_value=opener):
            with pytest.raises(urllib.error.HTTPError):
                web_discovery._http_get("https://example.gov/x", 10, 1000)
    fallback.assert_not_called()


def test_403_is_retried_once_with_the_browser_fingerprint():
    with mock.patch.object(
        web_discovery, "_browser_tls_get", return_value=(b"<html>real</html>", "text/html", "utf-8")
    ) as fallback:
        opener = mock.MagicMock()
        opener.open.side_effect = _http_error(403)
        with mock.patch.object(web_discovery.urllib.request, "build_opener", return_value=opener):
            body, ctype, charset = web_discovery._http_get("https://example.gov/x", 10, 1000)
    assert body == b"<html>real</html>"
    assert fallback.call_count == 1


def test_missing_dependency_fails_closed_and_keeps_the_403():
    """Without curl_cffi the source must go back to being a reported gap, not
    raise something the caller does not expect."""
    with mock.patch.object(web_discovery, "_browser_tls_get", side_effect=ImportError):
        opener = mock.MagicMock()
        opener.open.side_effect = _http_error(403)
        with mock.patch.object(web_discovery.urllib.request, "build_opener", return_value=opener):
            with pytest.raises(urllib.error.HTTPError) as caught:
                web_discovery._http_get("https://example.gov/x", 10, 1000)
    assert caught.value.code == 403


def test_fallback_still_refuses_an_off_host_redirect():
    """The stdlib path only follows redirects within the original host — a page
    that redirects off-site is not that page any more. The retry keeps that."""
    fake = mock.MagicMock(status_code=200, url="https://elsewhere.example/landing",
                          content=b"x", encoding="utf-8")
    fake.headers.get.return_value = "text/html"
    with mock.patch.dict("sys.modules", {"curl_cffi": mock.MagicMock(requests=mock.MagicMock(get=mock.MagicMock(return_value=fake)))}):
        with pytest.raises(urllib.error.HTTPError):
            web_discovery._browser_tls_get("https://example.gov/x", 10, 1000)


def test_fallback_raises_when_the_retry_is_also_refused():
    fake = mock.MagicMock(status_code=403, url="https://example.gov/x")
    with mock.patch.dict("sys.modules", {"curl_cffi": mock.MagicMock(requests=mock.MagicMock(get=mock.MagicMock(return_value=fake)))}):
        with pytest.raises(urllib.error.HTTPError):
            web_discovery._browser_tls_get("https://example.gov/x", 10, 1000)


def _cffi_returning(status, text="", url="https://example.gov/robots.txt"):
    resp = mock.MagicMock(status_code=status, text=text, url=url)
    return mock.MagicMock(requests=mock.MagicMock(get=mock.MagicMock(return_value=resp)))


class TestRobotsGate:
    """Looking like a browser is always subordinate to the site's stated policy."""

    def setup_method(self):
        web_discovery._ROBOTS_CACHE.clear()

    def teardown_method(self):
        web_discovery._ROBOTS_CACHE.clear()

    def test_blanket_permission_allows_the_retry(self):
        """fldoe.org serves exactly this: User-agent: * / Disallow:"""
        with mock.patch.dict("sys.modules", {"curl_cffi": _cffi_returning(200, "User-agent: *\nDisallow:\n")}):
            assert web_discovery._robots_allows("https://example.gov/grants/", 10) is True

    def test_a_disallow_rule_blocks_the_retry(self):
        with mock.patch.dict("sys.modules", {"curl_cffi": _cffi_returning(200, "User-agent: *\nDisallow: /grants\n")}):
            assert web_discovery._robots_allows("https://example.gov/grants/rfp", 10) is False

    def test_unreadable_robots_fails_closed(self):
        """A site we cannot get a policy from does not get bypassed."""
        with mock.patch.dict("sys.modules", {"curl_cffi": _cffi_returning(403)}):
            assert web_discovery._robots_allows("https://example.gov/grants/", 10) is False

    def test_absent_robots_is_treated_as_no_restrictions(self):
        with mock.patch.dict("sys.modules", {"curl_cffi": _cffi_returning(404)}):
            assert web_discovery._robots_allows("https://example.gov/grants/", 10) is True

    def test_an_exception_fails_closed(self):
        broken = mock.MagicMock(requests=mock.MagicMock(get=mock.MagicMock(side_effect=OSError("boom"))))
        with mock.patch.dict("sys.modules", {"curl_cffi": broken}):
            assert web_discovery._robots_allows("https://example.gov/grants/", 10) is False

    def test_the_answer_is_cached_per_origin(self):
        module = _cffi_returning(200, "User-agent: *\nDisallow:\n")
        with mock.patch.dict("sys.modules", {"curl_cffi": module}):
            web_discovery._robots_allows("https://example.gov/a", 10)
            web_discovery._robots_allows("https://example.gov/b", 10)
        assert module.requests.get.call_count == 1

    def test_a_disallowed_page_is_never_fetched(self):
        """The gate must stop the content request, not merely be consulted."""
        with mock.patch.object(web_discovery, "_robots_allows", return_value=False):
            with pytest.raises(urllib.error.HTTPError):
                web_discovery._browser_tls_get("https://example.gov/grants/", 10, 1000)


def test_fldoe_is_no_longer_registered_as_blocked():
    from openoutreach.funding.local_sources import LOCAL_SOURCES

    fldoe = next(s for s in LOCAL_SOURCES if s.key == "fl-doe-21cclc")
    assert not fldoe.is_blocked, "21st CCLC should be fetchable now"
