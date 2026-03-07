from django.apps import AppConfig


class IftfApp(AppConfig):
    name = 'iftf_duoverkoop'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Ensure login/logout signal receivers in src/core/models.py are registered.
        import iftf_duoverkoop.src.core.models  # noqa: F401
