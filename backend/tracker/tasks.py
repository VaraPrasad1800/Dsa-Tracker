from celery import shared_task
from django.contrib.auth import get_user_model
from tracker.services.reminders import get_or_create_daily_review_digest
from tracker.services.analytics import invalidate_user_analytics_cache

User = get_user_model()


@shared_task(name='tracker.tasks.send_daily_review_digest')
def send_daily_review_digest():
    """Send daily review digests and create in-app review-due notifications."""
    from tracker.services.notification_service import create_review_due_notification
    from tracker.services.leitner import get_leitner_box_stats

    summary = []
    for user in User.objects.all():
        digest = get_or_create_daily_review_digest(user)
        due_count = digest.get('due_count', 0)
        if due_count > 0:
            msg = f'[REMINDER] {user.username}: {due_count} problems due for review'
            print(msg)
            summary.append(msg)
            create_review_due_notification(user, due_count)
    return summary


@shared_task(name='tracker.tasks.refresh_user_analytics')
def refresh_user_analytics():
    """Invalidate analytics caches for all users so next request recomputes."""
    for user in User.objects.all():
        invalidate_user_analytics_cache(user.id)
    return 'Analytics cache refreshed for all users'


@shared_task(name='tracker.tasks.check_challenge_deadlines')
def check_challenge_deadlines():
    """
    Mark expired challenges and finalize completed ones.
    Run every 5 minutes via Celery Beat.
    Idempotent — safe to call multiple times.
    """
    from tracker.services.challenge_service import mark_expired_challenges
    mark_expired_challenges()
    return 'Challenge deadlines checked'


@shared_task(name='tracker.tasks.send_challenge_expiry_reminders')
def send_challenge_expiry_reminders():
    """
    Notify users whose active challenges expire within 30 minutes.
    Run every 5 minutes via Celery Beat.
    """
    from datetime import timedelta
    from django.utils import timezone
    from tracker.models import Challenge
    from tracker.services.notification_service import create_challenge_expiring_notification

    now = timezone.now()
    soon = now + timedelta(minutes=30)
    expiring = Challenge.objects.filter(
        status='ACTIVE',
        end_time__gte=now,
        end_time__lte=soon,
    ).select_related('user')

    for challenge in expiring:
        minutes_left = max(1, int(challenge.time_remaining_seconds / 60))
        create_challenge_expiring_notification(challenge.user, challenge.title, minutes_left)

    return f'Sent expiry reminders for {expiring.count()} challenges'


@shared_task(name='tracker.tasks.reset_weekly_points')
def reset_weekly_points():
    """
    Reset the weekly points bucket for all users.
    Run every Monday at 00:00 UTC via Celery Beat.
    """
    from tracker.services.points_service import reset_weekly_points as _reset
    count = 0
    for user in User.objects.all():
        _reset(user)
        count += 1
    return f'Weekly points reset for {count} users'


@shared_task(name='tracker.tasks.seed_achievements')
def seed_achievements():
    """Ensure all achievement definitions exist in the database. Idempotent."""
    from tracker.services.achievement_service import seed_achievements as _seed
    _seed()
    return 'Achievements seeded'


@shared_task(name='tracker.tasks.run_submission_task', queue='judge')
def run_submission_task(submission_id):
    """
    Asynchronously executes an Online Judge submission.
    Updates the Submission row with the verdict, metrics, and side effects.
    """
    from tracker.services.judge_service import execute_submission
    return execute_submission(str(submission_id))


@shared_task(name='tracker.tasks.cleanup_expired_tokens')
def cleanup_expired_tokens():
    """
    Delete expired or revoked refresh tokens older than 30 days.
    """
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Q
    from tracker.models import RefreshToken

    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = RefreshToken.objects.filter(
        Q(expires_at__lt=cutoff) | Q(revoked=True, revoked_at__lt=cutoff)
    ).delete()
    return f'Cleaned up {deleted_count} expired/revoked refresh tokens'

