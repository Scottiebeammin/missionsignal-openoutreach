import hashlib
from urllib.parse import urlsplit, urlunsplit


def normalize_text(value: str) -> str:
    return " ".join((value or "").casefold().split())


def normalize_canonical_url(url: str) -> str:
    """Normalize a URL for deterministic opportunity identity."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.casefold()
    hostname = (parts.hostname or "").casefold()
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        hostname = f"{hostname}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, hostname, path, "", ""))


def _digest(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def source_external_identity(source_key: str, external_id: str) -> str:
    return _digest(f"source:{normalize_text(source_key)}:{normalize_text(external_id)}")


def canonical_url_identity(url: str) -> str:
    return _digest(f"url:{normalize_canonical_url(url)}")


def composite_identity(*, funder_name: str, title: str, deadline, opportunity_type: str) -> str:
    deadline_value = deadline.isoformat() if deadline else ""
    value = "|".join([
        "composite",
        normalize_text(funder_name),
        normalize_text(title),
        deadline_value,
        normalize_text(opportunity_type),
    ])
    return _digest(value)


def build_identity_key(
    *,
    source_key: str = "",
    external_id: str = "",
    canonical_url: str = "",
    funder_name: str = "",
    title: str,
    deadline=None,
    opportunity_type: str = "",
) -> str:
    if canonical_url:
        return canonical_url_identity(canonical_url)
    if source_key and external_id:
        return source_external_identity(source_key, external_id)
    return composite_identity(
        funder_name=funder_name,
        title=title,
        deadline=deadline,
        opportunity_type=opportunity_type,
    )
