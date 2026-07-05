class GrantsGovError(Exception):
    """Raised when the Grants.gov API returns an error or unparseable response."""


class WebDiscoveryLLMUnavailable(Exception):
    """Raised when grounded web discovery needs the LLM extraction step but no
    usable LLM is configured in SiteConfig (missing key/model/provider deps)."""
