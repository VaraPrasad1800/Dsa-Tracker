"""
Notification service — creates and retrieves per-user in-app notifications.

Notifications are lightweight records.  They are NOT pushed via WebSocket
(that would require Django Channels).  The frontend polls /api/notifications/
every 60 seconds via TanStack Query.

SPAM PREVENTION
---------------
- We do not create duplicate notifications of the same type within a short
  window (DEDUP_WINDOW_MINUTES).
- Daily review due notifications are created at most once per day.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from tracker.models import Notification

DEDUP_WINDOW_MINUTES = 60  # suppress duplicate notifications within this window


def _recent_duplicate_exists(user, ntype: str, minutes: int = DEDUP_WINDOW_MINUTES) -> bool:
    cutoff = timezone.now() - timedelta(minutes=minutes)
    return Notification.objects.filter(
        user=user,
        type=ntype,
        created_at__gte=cutoff,
    ).exists()


@transaction.atomic
def create_notification(
    user,
    ntype: str,
    title: str,
    body: str = '',
    action_url: str = '',
    dedup: bool = True,
) -> Notification | None:
    """
    Create a notification for *user*.  If *dedup* is True and a notification
    of the same type was created within DEDUP_WINDOW_MINUTES, skip creation
    and return None.
    """
    if dedup and _recent_duplicate_exists(user, ntype):
        return None

    return Notification.objects.create(
        user=user,
        type=ntype,
        title=title,
        body=body,
        action_url=action_url,
    )


def get_notifications(user, unread_only: bool = False, limit: int = 50) -> list:
    """Return recent notifications for *user*."""
    qs = Notification.objects.filter(user=user)
    if unread_only:
        qs = qs.filter(is_read=False)
    return list(qs[:limit])


def get_unread_count(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


@transaction.atomic
def mark_read(user, notification_id) -> bool:
    """Mark a single notification as read.  Returns True if found and updated."""
    updated = Notification.objects.filter(user=user, id=notification_id).update(is_read=True)
    return updated > 0


@transaction.atomic
def mark_all_read(user) -> int:
    """Mark all unread notifications as read.  Returns count updated."""
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)


def create_review_due_notification(user, due_count: int):
    """Create a 'reviews due today' notification (at most once per day)."""
    cutoff = timezone.now() - timedelta(hours=20)  # ~once per day
    if Notification.objects.filter(user=user, type='REVIEW_DUE', created_at__gte=cutoff).exists():
        return None
    return create_notification(
        user,
        ntype='REVIEW_DUE',
        title=f'{due_count} review{"s" if due_count != 1 else ""} due today',
        body='Complete your Leitner reviews to maintain your progress.',
        action_url='review',
        dedup=False,
    )


def create_achievement_notification(user, achievement_name: str, points: int):
    return create_notification(
        user,
        ntype='ACHIEVEMENT_UNLOCKED',
        title=f'Achievement unlocked: {achievement_name}',
        body=f'You earned {points} bonus points.',
        action_url='achievements',
        dedup=False,  # always show achievement unlocks
    )


def create_challenge_completed_notification(user, challenge_title: str, points_earned: int):
    return create_notification(
        user,
        ntype='CHALLENGE_COMPLETED',
        title=f'Challenge completed: {challenge_title}',
        body=f'You earned {points_earned} points!',
        action_url='challenges',
        dedup=False,
    )


def create_challenge_expiring_notification(user, challenge_title: str, minutes_left: int):
    return create_notification(
        user,
        ntype='CHALLENGE_EXPIRING',
        title=f'Challenge ending soon: {challenge_title}',
        body=f'Only {minutes_left} minutes remaining!',
        action_url='challenges',
    )
