"""
Achievement service — deterministic achievement unlock logic.

RULES
-----
- Achievements are defined in the Achievement table (seeded by a migration).
- Unlocks are idempotent: UserAchievement has a unique_together constraint,
  so a second unlock attempt raises IntegrityError which we catch and ignore.
- No AI. Conditions are evaluated from Achievement model fields.
- Points from achievements are awarded via points_service after unlock.

SUPPORTED CONDITIONS (checked deterministically)
-------------------------------------------------
required_solve_count       → user total solved problems >= threshold
required_streak_days       → user current streak >= threshold
required_difficulty + required_solve_count → solved that many of that difficulty
required_tag_slug + required_solve_count   → solved that many in that tag
required_challenge_count   → completed challenges >= threshold
required_accepted_count    → total solved problems >= threshold
"""

from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from tracker.models import (
    Achievement, UserAchievement, UserProblemProgress,
    UserStreak, Challenge, ActivityEvent,
)

User = get_user_model()

# Seed data: list of dicts used by the data migration
ACHIEVEMENT_SEED = [
    {
        'code': 'FIRST_SOLVE', 'name': 'First Solve', 'icon': '🎯',
        'description': 'Solved your first problem.',
        'points': 20, 'required_solve_count': 1, 'sort_order': 1,
    },
    {
        'code': 'TEN_PROBLEMS', 'name': '10 Problems Solved', 'icon': '🔟',
        'description': 'Solved 10 problems.',
        'points': 50, 'required_solve_count': 10, 'sort_order': 2,
    },
    {
        'code': 'FIFTY_PROBLEMS', 'name': '50 Problems Solved', 'icon': '🏅',
        'description': 'Solved 50 problems.',
        'points': 150, 'required_solve_count': 50, 'sort_order': 3,
    },
    {
        'code': 'HUNDRED_PROBLEMS', 'name': '100 Problems Solved', 'icon': '💯',
        'description': 'Solved 100 problems.',
        'points': 500, 'required_solve_count': 100, 'sort_order': 4,
    },
    {
        'code': 'STREAK_7', 'name': '7-Day Streak', 'icon': '🔥',
        'description': 'Maintained a 7-day solving streak.',
        'points': 75, 'required_streak_days': 7, 'sort_order': 10,
    },
    {
        'code': 'STREAK_30', 'name': '30-Day Streak', 'icon': '🏆',
        'description': 'Maintained a 30-day solving streak.',
        'points': 300, 'required_streak_days': 30, 'sort_order': 11,
    },
    {
        'code': 'FIRST_HARD', 'name': 'Hard Knocks', 'icon': '💪',
        'description': 'Solved your first Hard problem.',
        'points': 100, 'required_difficulty': 'Hard', 'required_solve_count': 1, 'sort_order': 20,
    },
    {
        'code': 'TEN_MEDIUM', 'name': 'Medium Mastery', 'icon': '⚡',
        'description': 'Solved 10 Medium problems.',
        'points': 80, 'required_difficulty': 'Medium', 'required_solve_count': 10, 'sort_order': 21,
    },
    {
        'code': 'FIRST_CHALLENGE', 'name': 'Challenge Accepted', 'icon': '🎮',
        'description': 'Completed your first challenge.',
        'points': 50, 'required_challenge_count': 1, 'sort_order': 30,
    },
    {
        'code': 'FIVE_CHALLENGES', 'name': 'Challenge Champion', 'icon': '🥇',
        'description': 'Completed 5 challenges.',
        'points': 200, 'required_challenge_count': 5, 'sort_order': 31,
    },
    {
        'code': 'HUNDRED_ACCEPTED', 'name': '100 Problems Solved', 'icon': '✅',
        'description': 'Solved 100 problems.',
        'points': 300, 'required_accepted_count': 100, 'sort_order': 40,
    },
    {
        'code': 'GRAPH_SOLVER', 'name': 'Graph Guru', 'icon': '🕸️',
        'description': 'Solved 10 Graph problems.',
        'points': 100, 'required_tag_slug': 'graph', 'required_solve_count': 10, 'sort_order': 50,
    },
    {
        'code': 'DP_MASTER', 'name': 'DP Master', 'icon': '🧩',
        'description': 'Solved 10 Dynamic Programming problems.',
        'points': 150, 'required_tag_slug': 'dynamic-programming', 'required_solve_count': 10, 'sort_order': 51,
    },
]


def seed_achievements():
    """Create achievement records from ACHIEVEMENT_SEED.  Safe to call multiple times."""
    for data in ACHIEVEMENT_SEED:
        Achievement.objects.update_or_create(
            code=data['code'],
            defaults={k: v for k, v in data.items() if k != 'code'},
        )


def _count_solved(user) -> int:
    return UserProblemProgress.objects.filter(user=user, status='SOLVED').count()


def _count_solved_by_difficulty(user, difficulty: str) -> int:
    return UserProblemProgress.objects.filter(
        user=user, status='SOLVED', problem__difficulty=difficulty
    ).count()


def _count_solved_by_tag(user, tag_slug: str) -> int:
    return UserProblemProgress.objects.filter(
        user=user, status='SOLVED', problem__tags__slug=tag_slug
    ).count()


def _get_current_streak(user) -> int:
    try:
        return user.streak.current_streak
    except Exception:
        return 0


def _count_completed_challenges(user) -> int:
    return Challenge.objects.filter(user=user, status='COMPLETED').count()


def _count_accepted_submissions(user) -> int:
    return UserProblemProgress.objects.filter(user=user, status='SOLVED').count()


def _is_condition_met(achievement: Achievement, user) -> bool:
    """Return True if all non-null conditions on this achievement are met."""
    has_difficulty = bool(achievement.required_difficulty)
    has_tag = bool(achievement.required_tag_slug)
    has_solve = achievement.required_solve_count is not None
    has_streak = achievement.required_streak_days is not None
    has_challenge = achievement.required_challenge_count is not None
    has_accepted = achievement.required_accepted_count is not None

    if has_streak:
        if _get_current_streak(user) < achievement.required_streak_days:
            return False

    if has_solve:
        if has_difficulty:
            count = _count_solved_by_difficulty(user, achievement.required_difficulty)
        elif has_tag:
            count = _count_solved_by_tag(user, achievement.required_tag_slug)
        else:
            count = _count_solved(user)
        if count < achievement.required_solve_count:
            return False

    if has_challenge:
        if _count_completed_challenges(user) < achievement.required_challenge_count:
            return False

    if has_accepted:
        if _count_accepted_submissions(user) < achievement.required_accepted_count:
            return False

    return True


@transaction.atomic
def _try_unlock(user, achievement: Achievement) -> bool:
    """
    Attempt to create a UserAchievement record.
    Returns True if newly unlocked, False if already existed.
    """
    try:
        UserAchievement.objects.create(user=user, achievement=achievement)
        ActivityEvent.objects.create(
            user=user,
            event_type='ACHIEVEMENT_UNLOCKED',
            metadata={'achievement_code': achievement.code, 'points': achievement.points},
        )
        return True
    except IntegrityError:
        return False


def check_and_unlock_achievements(user) -> list[Achievement]:
    """
    Check all achievements the user hasn't unlocked yet.
    Unlock any whose conditions are now met.
    Returns list of newly unlocked Achievement objects.
    """
    from tracker.services.points_service import award_points
    from tracker.services.notification_service import create_achievement_notification

    unlocked_ids = set(
        UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
    )
    candidates = Achievement.objects.exclude(id__in=unlocked_ids)

    newly_unlocked = []
    for achievement in candidates:
        if _is_condition_met(achievement, user):
            if _try_unlock(user, achievement):
                newly_unlocked.append(achievement)
                if achievement.points > 0:
                    award_points(
                        user,
                        reason=f'achievement_{achievement.code}',
                        amount=achievement.points,
                    )
                create_achievement_notification(user, achievement.name, achievement.points)

    return newly_unlocked


def get_user_achievements(user) -> list[dict]:
    """Return all achievements with unlock status for this user."""
    unlocked_map = {
        ua.achievement_id: ua.unlocked_at
        for ua in UserAchievement.objects.filter(user=user).select_related('achievement')
    }
    result = []
    for ach in Achievement.objects.all():
        result.append({
            'code': ach.code,
            'name': ach.name,
            'description': ach.description,
            'icon': ach.icon,
            'points': ach.points,
            'unlocked': ach.id in unlocked_map,
            'unlocked_at': unlocked_map.get(ach.id),
        })
    return result
