# 管理调度器

from django.core.management.base import BaseCommand
from ...scheduler import start_scheduler


class Command(BaseCommand):
    help = 'Run APScheduler for scheduled tasks'

    def handle(self, *args, **options):
        start_scheduler()
