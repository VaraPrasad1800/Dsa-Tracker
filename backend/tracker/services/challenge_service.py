"""
Challenge service — create, manage, and score user challenges.

RULES
-----
- Challenges are server-authoritative: start/end times are set by the server.
- Points cannot be adjusted from the frontend.
- Challenge completion is detected by counting solved problems
  (or completed Leitner reviews for REVIEW template) after the challenge starts.
- On expiry (detected by Celery task), status → EXPIRED, partial points may apply.
- Scoring: base points if target_count reached; bonus_points if also within deadline.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from tracker.models import (
    Challenge, ChallengeProblem, Problem,
    UserProblemProgress, ReviewHistory,
)
from tracker.scoring import (
    POINTS_CHALLENGE_COMPLETION, POINTS_CHALLENGE_ON_TIME_BONUS,
)


# ---------------------------------------------------------------------------
# Challenge creation
# ---------------------------------------------------------------------------

@transaction.atomic
def create_challenge(user, data: dict) -> Challenge:
    """
    Create a challenge for *user*.

    Expected keys in *data*:
        title (str, required)
        description (str, optional)
        template (str, optional, default='CUSTOM')
        duration_minutes (int) OR end_time (ISO datetime str)
        target_count (int, required)
        problem_ids (list[str], optional — specific problems to include)
        points (int, optional — override; default computed from scoring constants)
        bonus_points (int, optional)
        topic_filter_id (str, optional)
        difficulty_filter (str, optional)
        company_filter_id (str, optional)
    """
    now = timezone.now()
    duration = int(data.get('duration_minutes', 1440))  # default 24 hours
    end_time = data.get('end_time')
    if end_time:
        from django.utils.dateparse import parse_datetime
        end_time = parse_datetime(end_time)
        if end_time is None or end_time <= now:
            raise ValueError('end_time must be a valid future datetime.')
    else:
        end_time = now + timedelta(minutes=max(1, duration))

    points = int(data.get('points', POINTS_CHALLENGE_COMPLETION))
    bonus = int(data.get('bonus_points', POINTS_CHALLENGE_ON_TIME_BONUS))

    challenge = Challenge.objects.create(
        user=user,
        title=data['title'],
        description=data.get('description', ''),
        template=data.get('template', 'CUSTOM'),
        start_time=now,
        end_time=end_time,
        target_count=max(1, int(data.get('target_count', 1))),
        points=points,
        bonus_points=bonus,
        status='ACTIVE',
        difficulty_filter=data.get('difficulty_filter', ''),
    )

    # Optional tag/company FK filters
    if data.get('topic_filter_id'):
        from tracker.models import Tag
        try:
            challenge.topic_filter = Tag.objects.get(id=data['topic_filter_id'])
        except (Tag.DoesNotExist, Exception):
            pass

    if data.get('company_filter_id'):
        from tracker.models import Company
        try:
            challenge.company_filter = Company.objects.get(id=data['company_filter_id'])
        except (Exception,):
            pass

    challenge.save()

    # Attach specific problems if provided
    problem_ids = data.get('problem_ids', [])
    if problem_ids:
        problems = Problem.objects.filter(id__in=problem_ids[:50])  # max 50 problems per challenge
        for prob in problems:
            ChallengeProblem.objects.get_or_create(challenge=challenge, problem=prob)

    return challenge


# ---------------------------------------------------------------------------
# Progress checking
# ---------------------------------------------------------------------------

def check_challenge_progress(user, challenge_id: str) -> dict:
    """
    Recompute and return the current progress for a challenge.
    Does NOT update the database; call update_challenge_status() to persist.
    """
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=user)
    except Challenge.DoesNotExist:
        return {}

    return _compute_progress(challenge, user)


def _compute_progress(challenge: Challenge, user) -> dict:
    """Compute how many challenge problems/conditions have been met."""
    now = timezone.now()

    if challenge.template == 'REVIEW':
        # Count completed Leitner reviews since challenge start
        completed = ReviewHistory.objects.filter(
            progress__user=user,
            action='SOLVED',
            created_at__gte=challenge.start_time,
        ).count()
    elif challenge.challenge_problems.exists():
        # Specific problem list — check solved problems after start
        completed = 0
        cp_list = challenge.challenge_problems.select_related('problem')
        for cp in cp_list:
            is_solved = UserProblemProgress.objects.filter(
                user=user,
                problem=cp.problem,
                status='SOLVED',
                updated_at__gte=challenge.start_time,
            ).exists() or ReviewHistory.objects.filter(
                progress__user=user,
                progress__problem=cp.problem,
                action='SOLVED',
                created_at__gte=challenge.start_time,
            ).exists()
            if is_solved and not cp.completed:
                cp.completed = True
                cp.completed_at = now
                cp.save(update_fields=['completed', 'completed_at'])
            if cp.completed:
                completed += 1
        if completed == 0:
            completed = _count_leitner_solved_for_challenge(challenge, user)
    else:
        # Filter-based: count solved problems matching filters
        completed = _count_filtered_solved(challenge, user)

    target = challenge.target_count
    is_complete = completed >= target
    is_expired = now > challenge.end_time
    is_on_time = is_complete and not is_expired

    return {
        'completed_count': completed,
        'target_count': target,
        'is_complete': is_complete,
        'is_expired': is_expired,
        'is_on_time': is_on_time,
        'time_remaining_seconds': max(0, (challenge.end_time - now).total_seconds()),
        'points': challenge.points,
        'bonus_points': challenge.bonus_points if is_on_time else 0,
    }


def _count_filtered_solved(challenge: Challenge, user) -> int:
    qs = UserProblemProgress.objects.filter(
        user=user,
        status='SOLVED',
        updated_at__gte=challenge.start_time,
    )
    if challenge.difficulty_filter:
        qs = qs.filter(problem__difficulty=challenge.difficulty_filter)
    if challenge.topic_filter:
        qs = qs.filter(problem__tags=challenge.topic_filter)
    if challenge.company_filter:
        qs = qs.filter(problem__companies=challenge.company_filter)
    count = qs.values('problem_id').distinct().count()
    if count == 0:
        return _count_leitner_solved_for_challenge(challenge, user)
    return count


def _count_leitner_solved_for_challenge(challenge: Challenge, user) -> int:
    """Count problems marked SOLVED via leitner (keyboard shortcut) since challenge start."""
    qs = ReviewHistory.objects.filter(
        progress__user=user,
        action='SOLVED',
        created_at__gte=challenge.start_time,
    )
    if challenge.difficulty_filter:
        qs = qs.filter(progress__problem__difficulty=challenge.difficulty_filter)
    if challenge.topic_filter:
        qs = qs.filter(progress__problem__tags=challenge.topic_filter)
    if challenge.company_filter:
        qs = qs.filter(progress__problem__companies=challenge.company_filter)
    return qs.values('progress__problem_id').distinct().count()


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

@transaction.atomic
def finalize_challenge(challenge: Challenge, user) -> dict:
    """
    Called when a challenge is either completed or expired.
    Awards points, creates notification.
    """
    from tracker.services.points_service import award_challenge_points
    from tracker.services.notification_service import create_challenge_completed_notification
    from tracker.models import ActivityEvent

    progress = _compute_progress(challenge, user)
    now = timezone.now()

    points_earned = 0
    if progress['is_complete']:
        bonus = progress['bonus_points']
        pts = award_challenge_points(user, challenge.points, bonus)
        points_earned = challenge.points + bonus
        challenge.status = 'COMPLETED'
        challenge.completed_at = now
        challenge.points_earned = points_earned
        challenge.completed_count = progress['completed_count']
        challenge.save()

        create_challenge_completed_notification(user, challenge.title, points_earned)

        ActivityEvent.objects.create(
            user=user,
            event_type='CHALLENGE_COMPLETED',
            metadata={
                'challenge_id': str(challenge.id),
                'points_earned': points_earned,
                'on_time': progress['is_on_time'],
            },
        )
    else:
        challenge.status = 'EXPIRED'
        challenge.completed_count = progress['completed_count']
        challenge.save()

    # Check achievements after challenge completion
    from tracker.services.achievement_service import check_and_unlock_achievements
    check_and_unlock_achievements(user)

    return {**progress, 'points_earned': points_earned, 'status': challenge.status}


@transaction.atomic
def mark_expired_challenges():
    """
    Celery Beat task: check all ACTIVE challenges that are past their end_time.
    Called every 5 minutes.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    now = timezone.now()
    overdue = Challenge.objects.filter(status='ACTIVE', end_time__lt=now).select_related('user')

    for challenge in overdue:
        user = challenge.user
        progress = _compute_progress(challenge, user)
        if progress['is_complete']:
            finalize_challenge(challenge, user)
        else:
            challenge.status = 'EXPIRED'
            challenge.completed_count = progress['completed_count']
            challenge.save()


def get_active_challenges(user) -> list:
    """Return user's active challenges with progress."""
    challenges = Challenge.objects.filter(user=user, status='ACTIVE').prefetch_related(
        'challenge_problems__problem', 'topic_filter', 'company_filter'
    )
    result = []
    for ch in challenges:
        progress = _compute_progress(ch, user)
        result.append({
            'id': str(ch.id),
            'title': ch.title,
            'description': ch.description,
            'template': ch.template,
            'start_time': ch.start_time.isoformat(),
            'end_time': ch.end_time.isoformat(),
            'target_count': ch.target_count,
            'points': ch.points,
            'bonus_points': ch.bonus_points,
            'status': ch.status,
            **progress,
        })
    return result


def get_challenge_history(user, limit: int = 20) -> list:
    """Return completed/expired challenge history."""
    challenges = Challenge.objects.filter(
        user=user, status__in=['COMPLETED', 'EXPIRED']
    ).order_by('-created_at')[:limit]
    return [
        {
            'id': str(ch.id),
            'title': ch.title,
            'template': ch.template,
            'status': ch.status,
            'target_count': ch.target_count,
            'completed_count': ch.completed_count,
            'points_earned': ch.points_earned,
            'completed_at': ch.completed_at.isoformat() if ch.completed_at else None,
            'created_at': ch.created_at.isoformat(),
        }
        for ch in challenges
    ]
