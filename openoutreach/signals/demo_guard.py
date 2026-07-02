"""
Keep demo/seed fiction out of real clients' views.

demo.py seeds demo entities (example.org/example.com websites) into the SHARED
reference tables (ResourceProvider, PartnerOrganization, Funder, SourceOrganization),
so every client-visible queryset must exclude them. RFC 2606 reserves example.*
domains, so a website containing "example." can never be a real organization.
"""


def exclude_demo(queryset):
    """Filter demo/placeholder rows (example.* websites) out of a reference queryset."""
    return queryset.exclude(website__icontains="example.")
