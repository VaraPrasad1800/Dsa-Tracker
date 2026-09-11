from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from tracker.models import Problem, UserProblemProgress, DailyStat, UserStreak, Tag, Company

CACHE_TTL = 6 * 3600  # 6 hours TTL per specification

def get_cache_key(prefix, user_id, extra=''):
    if extra:
        return f'analytics:{prefix}:{user_id}:{extra}'
    return f'analytics:{prefix}:{user_id}'

def invalidate_user_analytics_cache(user_id):
    current_year = timezone.now().year
    keys = [
        get_cache_key('heatmap', user_id, current_year),
        get_cache_key('heatmap', user_id, current_year - 1),
        get_cache_key('topic_breakdown', user_id),
        get_cache_key('streaks', user_id),
        get_cache_key('difficulty_breakdown', user_id),
        get_cache_key('timeline', user_id, 90),
        get_cache_key('timeline', user_id, 30),
        get_cache_key('dashboard', user_id),
        f'digest:{user_id}',
    ]
    for key in keys:
        cache.delete(key)

def update_user_streak(user, solved_date=None):
    if not solved_date:
        solved_date = timezone.now().date()
    streak, _ = UserStreak.objects.get_or_create(user=user)
    if not streak.last_solved_date:
        streak.current_streak = 1
        streak.longest_streak = max(streak.longest_streak, 1)
        streak.last_solved_date = solved_date
    elif streak.last_solved_date == solved_date:
        pass  # Already counted for today
    elif streak.last_solved_date == solved_date - timedelta(days=1):
        streak.current_streak += 1
        streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        streak.last_solved_date = solved_date
    elif streak.last_solved_date < solved_date - timedelta(days=1):
        streak.current_streak = 1
        streak.longest_streak = max(streak.longest_streak, 1)
        streak.last_solved_date = solved_date
    streak.save()
    return streak

def record_daily_stat(user, is_solved=False, problem=None, time_minutes=0):
    today = timezone.now().date()
    daily_stat, _ = DailyStat.objects.get_or_create(user=user, date=today)
    daily_stat.problems_attempted += 1
    if is_solved:
        daily_stat.problems_solved += 1
        update_user_streak(user, today)
        if problem:
            by_topic = daily_stat.by_topic or {}
            for tag in problem.tags.all():
                by_topic[tag.name] = by_topic.get(tag.name, 0) + 1
            daily_stat.by_topic = by_topic
    if time_minutes:
        daily_stat.total_time_minutes += time_minutes
    daily_stat.save()
    invalidate_user_analytics_cache(user.id)
    return daily_stat


def get_user_dashboard(user):
    """
    Lightweight placement-readiness dashboard summary.

    Combines: total solved, solved by difficulty, solved by company,
    streak, estimated placement readiness %, weak areas (topics + companies).
    """
    cache_key = get_cache_key('dashboard', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Global totals
    total_problems = Problem.objects.count()
    progresses = UserProblemProgress.objects.filter(user=user)
    solved_progress = progresses.filter(status='SOLVED')
    total_solved = solved_progress.count()
    total_revisit = progresses.filter(status='NEEDS_REVISIT').count()
    total_attempted = progresses.filter(times_attempted__gt=0).count()

    # Streaks
    streak_data = get_user_streaks(user)

    # Solved by difficulty
    difficulty_breakdown = {}
    for diff in ['Easy', 'Medium', 'Hard']:
        total = Problem.objects.filter(difficulty=diff).count()
        solved = solved_progress.filter(problem__difficulty=diff).count()
        pct = round((solved / total) * 100, 1) if total > 0 else 0
        difficulty_breakdown[diff] = {'solved': solved, 'total': total, 'percentage': pct}

    # Placement readiness heuristic (weighted toward medium/hard mastery)
    easy_pct = difficulty_breakdown['Easy']['percentage'] or 0
    med_pct = difficulty_breakdown['Medium']['percentage'] or 0
    hard_pct = difficulty_breakdown['Hard']['percentage'] or 0
    readiness = round(0.3 * easy_pct + 0.4 * med_pct + 0.3 * hard_pct, 1) if total_problems else 0
    readiness_band = 'Not Ready' if readiness < 30 else ('Progressing' if readiness < 60 else ('Interview Ready' if readiness < 85 else 'Placement Ready'))

    # Solved by company
    companies_solved = []
    for company in Company.objects.annotate(total=Count('problems', distinct=True)).filter(total__gt=0):
        solved = solved_progress.filter(problem__companies=company).count()
        companies_solved.append({
            'name': company.name,
            'slug': company.slug,
            'total': company.total,
            'solved': solved,
            'percentage': round((solved / company.total) * 100, 1) if company.total > 0 else 0,
        })
    companies_solved.sort(key=lambda x: x['percentage'])

    # Weak areas: topics below 50% solve rate
    topic_data = get_user_topic_breakdown(user)
    weak_topics = [t for t in topic_data['topics'] if t['is_weak']][:8]
    weak_companies = [c for c in companies_solved if c['percentage'] < 50.0][:8]

    # Recommended next difficulty progression
    next_difficulty = 'Easy'
    if easy_pct >= 80:
        next_difficulty = 'Medium' if med_pct < 80 else 'Hard'

    result = {
        'total_problems': total_problems,
        'total_solved': total_solved,
        'total_revisit': total_revisit,
        'total_attempted': total_attempted,
        'total_time_minutes': progresses.aggregate(total=Sum('total_time_spent_minutes'))['total'] or 0,
        'current_streak': streak_data['current_streak'],
        'longest_streak': streak_data['longest_streak'],
        'difficulty_breakdown': difficulty_breakdown,
        'placement_readiness': {
            'score': min(readiness, 100.0),
            'band': readiness_band,
            'next_difficulty': next_difficulty,
        },
        'solved_by_company': companies_solved,
        'weak_topics': weak_topics,
        'weak_companies': weak_companies,
    }
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result

def get_user_heatmap(user, year=None):
    if not year:
        year = timezone.now().year
    cache_key = get_cache_key('heatmap', user.id, year)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    stats = DailyStat.objects.filter(user=user, date__year=year)
    stat_dict = {stat.date.strftime('%Y-%m-%d'): stat.problems_solved for stat in stats}

    # Generate full year entries
    start_date = timezone.datetime(year, 1, 1).date()
    end_date = timezone.datetime(year, 12, 31).date()
    data = []
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime('%Y-%m-%d')
        data.append({'date': d_str, 'count': stat_dict.get(d_str, 0)})
        curr += timedelta(days=1)

    result = {'data': data, 'year': year}
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result

def get_user_topic_breakdown(user):
    cache_key = get_cache_key('topic_breakdown', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    tags = Tag.objects.annotate(
        total_problems=Count('problems', distinct=True)
    ).filter(total_problems__gt=0)

    topics = []
    for tag in tags:
        solved_count = UserProblemProgress.objects.filter(
            user=user,
            problem__tags=tag,
            status='SOLVED'
        ).count()
        percentage = round((solved_count / tag.total_problems) * 100, 1) if tag.total_problems > 0 else 0
        topics.append({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'solved': solved_count,
            'total': tag.total_problems,
            'percentage': percentage,
            'is_weak': percentage < 50.0
        })

    topics.sort(key=lambda x: x['percentage'])
    result = {'topics': topics}
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result

def get_user_streaks(user):
    cache_key = get_cache_key('streaks', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    streak, _ = UserStreak.objects.get_or_create(user=user)
    # Check if streak has lapsed (last solved date was before yesterday)
    today = timezone.now().date()
    current = streak.current_streak
    if streak.last_solved_date and streak.last_solved_date < today - timedelta(days=1):
        current = 0

    result = {
        'current_streak': current,
        'longest_streak': streak.longest_streak,
        'last_solved_date': streak.last_solved_date.strftime('%Y-%m-%d') if streak.last_solved_date else None,
    }
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result

def get_user_difficulty_breakdown(user):
    cache_key = get_cache_key('difficulty_breakdown', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    breakdown = {}
    for diff in ['Easy', 'Medium', 'Hard']:
        total = Problem.objects.filter(difficulty=diff).count()
        solved = UserProblemProgress.objects.filter(
            user=user,
            problem__difficulty=diff,
            status='SOLVED'
        ).count()
        breakdown[diff] = {
            'solved': solved,
            'total': total,
            'percentage': round((solved / total) * 100, 1) if total > 0 else 0
        }

    cache.set(cache_key, breakdown, timeout=CACHE_TTL)
    return breakdown

def get_user_timeline(user, days=90):
    cache_key = get_cache_key('timeline', user.id, days)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    since_date = timezone.now().date() - timedelta(days=days)
    stats = DailyStat.objects.filter(user=user, date__gte=since_date).order_by('date')
    stat_dict = {stat.date.strftime('%Y-%m-%d'): {
        'problems_solved': stat.problems_solved,
        'problems_attempted': stat.problems_attempted,
        'total_time_minutes': stat.total_time_minutes
    } for stat in stats}

    timeline = []
    curr = since_date
    today = timezone.now().date()
    while curr <= today:
        d_str = curr.strftime('%Y-%m-%d')
        info = stat_dict.get(d_str, {'problems_solved': 0, 'problems_attempted': 0, 'total_time_minutes': 0})
        timeline.append({
            'date': d_str,
            'problems_solved': info['problems_solved'],
            'problems_attempted': info['problems_attempted'],
            'total_time_minutes': info['total_time_minutes'],
        })
        curr += timedelta(days=1)

    cache.set(cache_key, timeline, timeout=CACHE_TTL)
    return timeline
