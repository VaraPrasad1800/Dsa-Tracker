from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from tracker.models import RefreshToken


class Command(BaseCommand):
    help = 'Clean up expired or revoked refresh tokens older than 30 days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Retention period in days for expired/revoked tokens (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count, _ = RefreshToken.objects.filter(
            Q(expires_at__lt=cutoff) | Q(revoked=True, revoked_at__lt=cutoff)
        ).delete()
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {deleted_count} tokens older than {days} days.'
        ))
