from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from tracker.models import Problem, UserProblemProgress, DailyStat, UserStreak, Tag, Company
from tracker.scoring import MASTERY_LEVELS, WEAK_TOPIC_THRESHOLD_PCT

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
        get_cache_key('topic_mastery', user_id),
        get_cache_key('streaks', user_id),
        get_cache_key('difficulty_breakdown', user_id),
        get_cache_key('timeline', user_id, 90),
        get_cache_key('timeline', user_id, 30),
        get_cache_key('dashboard', user_id),
        get_cache_key('revision_queue', user_id),
        f'digest:{user_id}',
    ]
    try:
        cache.delete_many(keys)
    except Exception:
        pass

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


# ============================================================================
# V2 ANALYTICS — Topic Mastery Levels, Revision Queue, Company Track
# ============================================================================

def _compute_mastery_level(solved_count: int, total: int, medium_hard_solved: int) -> str:
    """
    Deterministic mastery level based on MASTERY_LEVELS from scoring.py.
    Levels (weakest to strongest): Beginner, Familiar, Practicing, Strong, Mastered.
    MASTERY_LEVELS entries: (name, min_pct, min_solved, min_medium_hard)
    """
    pct = (solved_count / total * 100) if total > 0 else 0
    # Iterate from strongest to weakest, return first level met
    for name, min_pct, min_solved, min_mh in reversed(MASTERY_LEVELS):
        if pct >= min_pct and solved_count >= min_solved and medium_hard_solved >= min_mh:
            return name
    return 'Beginner'


def get_topic_mastery_levels(user) -> dict:
    """
    Return enhanced topic mastery with 5-level deterministic labels.
    Beginner → Familiar → Practicing → Strong → Mastered
    """
    cache_key = get_cache_key('topic_mastery', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    tags = Tag.objects.annotate(
        total_problems=Count('problems', distinct=True)
    ).filter(total_problems__gt=0)

    topics = []
    for tag in tags:
        progresses = UserProblemProgress.objects.filter(
            user=user, problem__tags=tag, status='SOLVED'
        ).select_related('problem')

        solved_count = progresses.count()
        medium_hard_solved = progresses.filter(
            problem__difficulty__in=['Medium', 'Hard']
        ).count()

        level = _compute_mastery_level(solved_count, tag.total_problems, medium_hard_solved)
        pct = round((solved_count / tag.total_problems) * 100, 1) if tag.total_problems > 0 else 0

        topics.append({
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
            'solved': solved_count,
            'total': tag.total_problems,
            'medium_hard_solved': medium_hard_solved,
            'percentage': pct,
            'mastery_level': level,
            'is_weak': pct < WEAK_TOPIC_THRESHOLD_PCT,
        })

    # Sort: weakest first (for actionable order)
    topics.sort(key=lambda x: (x['percentage'], x['solved']))
    result = {'topics': topics}
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result


def get_revision_queue(user) -> list:
    """
    Build a deterministic revision queue ordered by priority:
    1. Overdue Box 1 (most urgent)
    2. Overdue higher-box cards
    3. NEEDS_REVISIT problems
    4. Problems with recent failed submissions
    5. Recently solved problems (for reinforcement)

    Returns a list of safe dicts (no hidden test data).
    """
    cache_key = get_cache_key('revision_queue', user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from tracker.scoring import (
        REVISION_ORDER_OVERDUE_BOX1, REVISION_ORDER_OVERDUE_HIGHER_BOX,
        REVISION_ORDER_NEEDS_REVISIT, REVISION_ORDER_FAILED_SUBMISSION,
        REVISION_ORDER_RECENTLY_SOLVED,
    )

    now = timezone.now()
    queue = []
    seen_problem_ids = set()

    # 1 & 2: Overdue Leitner cards
    overdue = UserProblemProgress.objects.filter(
        user=user, next_review_date__lte=now
    ).select_related('problem').order_by('current_box', 'next_review_date')

    for prog in overdue:
        if prog.problem_id in seen_problem_ids:
            continue
        seen_problem_ids.add(prog.problem_id)
        priority = REVISION_ORDER_OVERDUE_BOX1 if prog.current_box == 1 else REVISION_ORDER_OVERDUE_HIGHER_BOX
        queue.append({
            'priority': priority,
            'problem_id': str(prog.problem_id),
            'question_number': prog.problem.question_number,
            'problem_title': prog.problem.title,
            'difficulty': prog.problem.difficulty,
            'status': prog.status,
            'leitner_box': prog.current_box,
            'next_review_date': prog.next_review_date.isoformat() if prog.next_review_date else None,
            'reason': 'overdue_review',
        })

    # 3: NEEDS_REVISIT (not already in queue)
    revisit = UserProblemProgress.objects.filter(
        user=user, status='NEEDS_REVISIT'
    ).select_related('problem').exclude(problem_id__in=seen_problem_ids)

    for prog in revisit:
        seen_problem_ids.add(prog.problem_id)
        queue.append({
            'priority': REVISION_ORDER_NEEDS_REVISIT,
            'problem_id': str(prog.problem_id),
            'question_number': prog.problem.question_number,
            'problem_title': prog.problem.title,
            'difficulty': prog.problem.difficulty,
            'status': prog.status,
            'leitner_box': prog.current_box,
            'next_review_date': None,
            'reason': 'needs_revisit',
        })

    # 4: Recently attempted problems (in last 7 days, not already in queue)
    week_ago = now - timedelta(days=7)
    attempted = UserProblemProgress.objects.filter(
        user=user,
        status='ATTEMPTED',
        updated_at__gte=week_ago,
    ).select_related('problem').exclude(problem_id__in=seen_problem_ids).order_by('-updated_at')

    for prog in attempted[:10]:
        if prog.problem_id in seen_problem_ids:
            continue
        seen_problem_ids.add(prog.problem_id)
        queue.append({
            'priority': REVISION_ORDER_FAILED_SUBMISSION,
            'problem_id': str(prog.problem_id),
            'question_number': prog.problem.question_number,
            'problem_title': prog.problem.title,
            'difficulty': prog.problem.difficulty,
            'status': 'ATTEMPTED',
            'leitner_box': prog.current_box,
            'next_review_date': None,
            'reason': 'attempted_problem',
        })

    # 5: Recently solved (last 3 days, for reinforcement)
    three_days_ago = now - timedelta(days=3)
    recent_solved = UserProblemProgress.objects.filter(
        user=user, status='SOLVED', last_solved__gte=three_days_ago
    ).select_related('problem').exclude(problem_id__in=seen_problem_ids).order_by('-last_solved')

    for prog in recent_solved[:5]:
        seen_problem_ids.add(prog.problem_id)
        queue.append({
            'priority': REVISION_ORDER_RECENTLY_SOLVED,
            'problem_id': str(prog.problem_id),
            'question_number': prog.problem.question_number,
            'problem_title': prog.problem.title,
            'difficulty': prog.problem.difficulty,
            'status': prog.status,
            'leitner_box': prog.current_box,
            'next_review_date': None,
            'reason': 'recently_solved',
        })

    # Sort by priority (ascending = most urgent first)
    queue.sort(key=lambda x: (x['priority'], x.get('leitner_box') or 99))
    cache.set(cache_key, queue, timeout=300)  # short TTL — revision queue changes often
    return queue


def get_company_track(user, company_slug: str) -> dict:
    """
    Return company preparation track data for a specific company.
    Shows solved/total, difficulty breakdown, weak topics, mastery.
    """
    try:
        company = Company.objects.get(slug=company_slug)
    except Company.DoesNotExist:
        return {}

    problems = Problem.objects.filter(companies=company).prefetch_related('tags')
    total = problems.count()
    if total == 0:
        return {'company': company.name, 'slug': company.slug, 'total': 0}

    solved_progress = UserProblemProgress.objects.filter(
        user=user, status='SOLVED', problem__companies=company
    )
    solved = solved_progress.count()

    # Difficulty breakdown
    difficulty_data = {}
    for diff in ['Easy', 'Medium', 'Hard']:
        diff_total = problems.filter(difficulty=diff).count()
        diff_solved = solved_progress.filter(problem__difficulty=diff).count()
        difficulty_data[diff] = {
            'total': diff_total,
            'solved': diff_solved,
            'percentage': round((diff_solved / diff_total * 100), 1) if diff_total > 0 else 0,
        }

    # Tag breakdown for this company
    from django.db.models import Count
    tag_counts = Tag.objects.filter(
        problems__companies=company
    ).annotate(
        total_in_company=Count('problems', filter=Q(problems__companies=company), distinct=True)
    ).filter(total_in_company__gt=0)

    weak_topics = []
    for tag in tag_counts:
        tag_solved = solved_progress.filter(problem__tags=tag).count()
        tag_pct = (tag_solved / tag.total_in_company * 100) if tag.total_in_company > 0 else 0
        if tag_pct < WEAK_TOPIC_THRESHOLD_PCT:
            weak_topics.append({
                'name': tag.name,
                'slug': tag.slug,
                'solved': tag_solved,
                'total': tag.total_in_company,
                'percentage': round(tag_pct, 1),
            })

    weak_topics.sort(key=lambda x: x['percentage'])
    overall_pct = round((solved / total * 100), 1) if total > 0 else 0

    return {
        'company': company.name,
        'slug': company.slug,
        'total': total,
        'solved': solved,
        'percentage': overall_pct,
        'difficulty_breakdown': difficulty_data,
        'weak_topics': weak_topics[:8],
        'readiness': 'Strong' if overall_pct >= 70 else ('Progressing' if overall_pct >= 40 else 'Needs Work'),
    }
