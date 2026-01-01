from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import signals to hook group membership → is_staff
        try:
            import accounts.signals  # noqa: F401
        except Exception:
            # Fail silently to avoid import-time crashes during migrations
            pass
