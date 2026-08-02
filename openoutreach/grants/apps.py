from django.apps import AppConfig


class GrantsConfig(AppConfig):
    name = "openoutreach.grants"
    label = "grants"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Atlas Grant Builder"
