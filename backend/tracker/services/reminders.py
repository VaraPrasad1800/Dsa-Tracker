from django.utils import timezone
from django.core.cache import cache
from tracker.models import UserProblemProgress

def get_or_create_daily_review_digest(user):
    cache_key = f'digest:{user.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    now = timezone.now()
    due_progresses = UserProblemProgress.objects.filter(
        user=user,
        next_review_date__lte=now
    ).select_related('problem').order_by('current_box', 'last_attempted')

    problems = []
    for p in due_progresses[:15]:
        problems.append({
            'problem_id': str(p.problem.id),
            'title': p.problem.title,
            'difficulty': p.problem.difficulty,
            'current_box': p.current_box,
            'source_url': p.problem.source_url,
        })

    digest = {
        'user_id': user.id,
        'username': user.username,
        'due_count': due_progresses.count(),
        'timestamp': now.isoformat(),
        'sample_problems': problems,
    }

    cache.set(cache_key, digest, timeout=86400)
    return digest
