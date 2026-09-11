from django.core.management.base import BaseCommand
from tracker.tasks import send_daily_review_digest, refresh_user_analytics

class Command(BaseCommand):
    help = 'Manually trigger scheduled tasks for review digest and analytics refresh'

    def handle(self, *args, **options):
        self.stdout.write('Running daily review digest task...')
        digest_res = send_daily_review_digest()
        self.stdout.write(f'Review digest result: {digest_res}')

        self.stdout.write('Running analytics refresh task...')
        analytics_res = refresh_user_analytics()
        self.stdout.write(f'Analytics refresh result: {analytics_res}')

        self.stdout.write(self.style.SUCCESS('All daily tasks executed successfully!'))
