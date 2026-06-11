from django.apps import AppConfig
import os


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Вакансии'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            from .telegram_bot import start_bot
            start_bot()