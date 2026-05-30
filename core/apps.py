from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Вакансии'

    def ready(self):
        from .telegram_bot import start_bot
        start_bot()