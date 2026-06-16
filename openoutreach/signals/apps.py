from django.apps import AppConfig


class SignalsConfig(AppConfig):
    name = "openoutreach.signals"
    label = "signals"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "MissionSignal"
