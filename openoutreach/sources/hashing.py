import hashlib
import json


def canonicalize_filters(filters: dict) -> str:
    """Return a deterministic JSON representation of search filters."""
    return json.dumps(filters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_filters(filters: dict) -> str:
    """Return the SHA-256 digest of canonically serialized search filters."""
    canonical = canonicalize_filters(filters)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
