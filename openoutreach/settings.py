# openoutreach/settings.py
"""
Minimal Django settings for using DjangoCRM's ORM + admin.
"""
import os
import sys
from urllib.parse import parse_qsl, urlparse
from pathlib import Path

# Playwright's sync API runs inside an async event loop, which triggers
# Django's async-safety check. We only use the ORM synchronously, so this is safe.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

ROOT_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = ROOT_DIR

def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("Only postgres:// or postgresql:// DATABASE_URL values are supported.")
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }
    options = dict(parse_qsl(parsed.query))
    if options:
        config["OPTIONS"] = options
    return config


_DEFAULT_SECRET = "openoutreach-local-dev-key-change-in-production"  # noqa: S105
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)

DEBUG = _env_bool("DEBUG", False)

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"] if DEBUG else [])

# Guard: crash loudly if the default secret key reaches a non-debug environment.
if not DEBUG and SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "SECRET_KEY is set to the default development value and DEBUG is False. "
        "Set the SECRET_KEY environment variable before running in production."
    )
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", [])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "openoutreach.admin_config.AnansiAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "openoutreach.crm.apps.CrmConfig",
    "openoutreach.chat.apps.ChatConfig",
    "openoutreach.core.apps.CoreConfig",
    "openoutreach.linkedin.apps.LinkedInConfig",
    "openoutreach.emails.apps.EmailsConfig",
    "openoutreach.signals.apps.SignalsConfig",
    "openoutreach.sources.apps.SourcesConfig",
    "openoutreach.funding.apps.FundingConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "openoutreach.core.middleware.ViewAsClientBanner",
]

ROOT_URLCONF = "openoutreach.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "openoutreach.core.context_processors.onboarding",
            ],
        },
    },
]

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(ROOT_DIR / "data" / "db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

STATIC_URL = "/static/"
STATIC_ROOT = ROOT_DIR / "staticfiles"

# WhiteNoise serves static files directly from gunicorn in production (no separate
# static host / CDN needed). Compressed storage gzips assets; non-manifest variant
# avoids hashed-filename lookups that would 500 on any un-collected reference.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = ROOT_DIR / "media"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/portal/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
# STARTTLS (port 587) or implicit SSL (port 465). Set one to true in prod; never both.
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "15"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@localhost")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = "CRM: "

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

TESTING = sys.argv[1:2] == ["test"]

# ── Unfold Admin ─────────────────────────────────────────────────────────────
UNFOLD = {
    "SITE_TITLE": "Anansi Atlas",
    "SITE_HEADER": "Anansi Atlas",
    "SITE_SUBHEADER": "Operator Console",
    "SITE_URL": "/operator/",
    "SITE_ICON": {
        "light": lambda request: "/static/signals/anansi-atlas-logo.png",
        "dark":  lambda request: "/static/signals/anansi-atlas-logo.png",
    },
    "COLORS": {
        "primary": {
            "50":  "250 244 230",
            "100": "245 235 205",
            "200": "235 210 155",
            "300": "225 185 105",
            "400": "215 165 65",
            "500": "201 144 30",
            "600": "175 120 20",
            "700": "145 95 15",
            "800": "110 70 10",
            "900": "75 45 5",
            "950": "45 25 2",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Operator",
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/operator/",
                    },
                    {
                        "title": "Organizations",
                        "icon": "business",
                        "link": "/operator/organizations/",
                    },
                    {
                        "title": "Waitlist",
                        "icon": "list",
                        "link": "/operator/waitlist/",
                    },
                ],
            },
            {
                "title": "Data",
                "items": [
                    {
                        "title": "Projects",
                        "icon": "folder",
                        "link": "/admin/core/project/",
                    },
                    {
                        "title": "Funders",
                        "icon": "payments",
                        "link": "/admin/funding/funder/",
                    },
                    {
                        "title": "Opportunities",
                        "icon": "star",
                        "link": "/admin/funding/opportunity/",
                    },
                    {
                        "title": "Partners",
                        "icon": "handshake",
                        "link": "/admin/funding/partnerorganization/",
                    },
                    {
                        "title": "Signups",
                        "icon": "person_add",
                        "link": "/admin/signals/interestsignup/",
                    },
                ],
            },
            {
                "title": "Config",
                "items": [
                    {
                        "title": "Site Configuration",
                        "icon": "settings",
                        "link": "/admin/core/siteconfig/",
                    },
                    {
                        "title": "Users",
                        "icon": "manage_accounts",
                        "link": "/admin/auth/user/",
                    },
                ],
            },
        ],
    },
}
