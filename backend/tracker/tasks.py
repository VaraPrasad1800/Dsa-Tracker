from celery import shared_task
from django.contrib.auth import get_user_model
from tracker.services.reminders import get_or_create_daily_review_digest
from tracker.services.analytics import invalidate_user_analytics_cache

User = get_user_model()

@shared_task(name='tracker.tasks.send_daily_review_digest')
def send_daily_review_digest():
    summary = []
    for user in User.objects.all():
        digest = get_or_create_daily_review_digest(user)
        due_count = digest.get('due_count', 0)
        if due_count > 0:
            msg = f'[REMINDER] {user.username}: {due_count} problems due for review'
            print(msg)
            summary.append(msg)
    return summary

@shared_task(name='tracker.tasks.refresh_user_analytics')
def refresh_user_analytics():
    for user in User.objects.all():
        invalidate_user_analytics_cache(user.id)
    return 'Analytics cache refreshed for all users'
