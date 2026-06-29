from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
    protocol = "https"

    def items(self):
        return [
            "home",
            "nonprofit-grant-research",
            "nonprofit-funding-intelligence",
            "opportunity-mapping-nonprofits",
            "nonprofit-readiness-assessment",
        ]

    def location(self, item):
        return reverse(item)


class LandingPageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return ["anansi-atlas-landing"]

    def location(self, item):
        return reverse(item)
