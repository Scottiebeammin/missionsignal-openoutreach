class GrantBuilderError(Exception):
    """Base for expected, recoverable Grant Builder failures surfaced to the user."""


class DraftGenerationUnavailable(GrantBuilderError):
    """Raised when drafting needs the LLM but no usable LLM is configured in SiteConfig."""


class DraftGenerationFailed(GrantBuilderError):
    """Raised when the LLM returned something Atlas cannot use as a draft response."""
