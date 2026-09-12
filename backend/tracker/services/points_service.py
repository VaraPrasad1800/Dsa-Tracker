"""
Points service — awards points server-side and records ActivityEvents.

All point operations go through this module.  No point can be awarded
from the frontend — the client receives the resulting total as read-only data.

IDEMPOTENCY
-----------
Some events (e.g. first solve of a problem) should only award points once.
The caller is responsible for checking whether the event already occurred
(e.g. checking if UserProblemProgress.times_solved == 1 before calling).
This service does NOT enforce idempotency internally except through the
atomic get_or_create for UserPoints.
"""

from django.db import transaction
from django.contrib.auth import get_user_model

from tracker.models import UserPoints, ActivityEvent

User = get_user_model()


def _get_or_create_points(user) -> UserPoints:
    pts, _ = UserPoints.objects.get_or_create(user=user)
    return pts


@transaction.atomic
def award_points(user, reason: str, amount: int, metadata: dict = None) -> UserPoints:
    """
    Add *amount* points to *user*'s total.  Records an ActivityEvent.

    Args:
        user: the User instance
        reason: human-readable reason string (stored in event metadata)
        amount: positive integer
        metadata: optional extra dict stored in the ActivityEvent

    Returns:
        Updated UserPoints instance.
    """
    if amount <= 0:
        return _get_or_create_points(user)

    pts = _get_or_create_points(user)
    pts.total += amount
    pts.weekly += amount
    pts.save(update_fields=['total', 'weekly', 'updated_at'])

    event_meta = {'points': amount, 'reason': reason}
    if metadata:
        event_meta.update(metadata)

    ActivityEvent.objects.create(
        user=user,
        event_type='POINTS_AWARDED',
        metadata=event_meta,
    )

    return pts


@transaction.atomic
def award_challenge_points(user, amount: int, bonus: int = 0) -> UserPoints:
    """Award challenge completion points (challenge_points bucket + total)."""
    pts = _get_or_create_points(user)
    total_award = amount + bonus
    pts.total += total_award
    pts.weekly += total_award
    pts.challenge_points += total_award
    pts.save(update_fields=['total', 'weekly', 'challenge_points', 'updated_at'])

    ActivityEvent.objects.create(
        user=user,
        event_type='POINTS_AWARDED',
        metadata={'points': total_award, 'reason': 'challenge_completion', 'bonus': bonus},
    )
    return pts


@transaction.atomic
def award_streak_points(user, streak_days: int, amount: int) -> UserPoints:
    """Award streak milestone points (streak_points bucket + total)."""
    pts = _get_or_create_points(user)
    pts.total += amount
    pts.weekly += amount
    pts.streak_points += amount
    pts.save(update_fields=['total', 'weekly', 'streak_points', 'updated_at'])

    ActivityEvent.objects.create(
        user=user,
        event_type='POINTS_AWARDED',
        metadata={'points': amount, 'reason': f'streak_{streak_days}_days'},
    )
    return pts


def get_user_points(user) -> dict:
    """Return the user's current point totals as a safe dict."""
    pts = _get_or_create_points(user)
    return {
        'total': pts.total,
        'weekly': pts.weekly,
        'challenge_points': pts.challenge_points,
        'streak_points': pts.streak_points,
    }


@transaction.atomic
def reset_weekly_points(user) -> UserPoints:
    """Reset the weekly bucket (called by a Celery Beat task every Monday)."""
    import datetime
    pts = _get_or_create_points(user)
    pts.weekly = 0
    pts.last_weekly_reset = datetime.date.today()
    pts.save(update_fields=['weekly', 'last_weekly_reset', 'updated_at'])
    return pts
