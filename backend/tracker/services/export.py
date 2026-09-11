"""
Export services for DSA Tracker.

Provides functionality to export user progress data in various formats:
- JSON (complete data dump)
- CSV (problem progress)
- Markdown (human-readable summary)
"""
import json
import csv
import io
from datetime import datetime
from django.contrib.auth import get_user_model
from tracker.models import (
    Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay
)

User = get_user_model()


def export_user_progress_json(user):
    """
    Export all user progress data as a JSON-serializable dictionary.

    Returns a dict with:
    - user info
    - problems progress
    - review history
    - daily stats
    - streaks
    - study plans
    """
    progresses = UserProblemProgress.objects.filter(user=user).select_related('problem').prefetch_related('problem__tags', 'problem__companies')
    histories = ReviewHistory.objects.filter(progress__user=user).select_related('progress__problem')
    daily_stats = DailyStat.objects.filter(user=user).order_by('-date')
    streak = UserStreak.objects.filter(user=user).first()
    study_plans = StudyPlan.objects.filter(user=user).prefetch_related('days__problems')

    return {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        },
        'problems': [
            {
                'problem_id': str(p.problem.id),
                'title': p.problem.title,
                'slug': p.problem.slug,
                'difficulty': p.problem.difficulty,
                'tags': [t.name for t in p.problem.tags.all()],
                'companies': [c.name for c in p.problem.companies.all()],
                'source_url': p.problem.source_url,
                'status': p.status,
                'times_solved': p.times_solved,
                'times_attempted': p.times_attempted,
                'last_attempted': p.last_attempted.isoformat() if p.last_attempted else None,
                'last_solved': p.last_solved.isoformat() if p.last_solved else None,
                'notes': p.notes,
                'code_solution': p.code_solution,
                'current_box': p.current_box,
                'next_review_date': p.next_review_date.isoformat() if p.next_review_date else None,
                'reviews_count': p.reviews_count,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat(),
            }
            for p in progresses
        ],
        'review_history': [
            {
                'problem_id': str(h.progress.problem.id),
                'problem_title': h.progress.problem.title,
                'old_box': h.old_box,
                'new_box': h.new_box,
                'action': h.action,
                'notes': h.notes,
                'created_at': h.created_at.isoformat(),
            }
            for h in histories
        ],
        'daily_stats': [
            {
                'date': d.date.isoformat(),
                'problems_solved': d.problems_solved,
                'problems_attempted': d.problems_attempted,
                'total_time_minutes': d.total_time_minutes,
                'by_topic': d.by_topic,
            }
            for d in daily_stats
        ],
        'streak': {
            'current_streak': streak.current_streak if streak else 0,
            'longest_streak': streak.longest_streak if streak else 0,
            'last_solved_date': streak.last_solved_date.isoformat() if streak and streak.last_solved_date else None,
        } if streak else None,
        'study_plans': [
            {
                'id': str(sp.id),
                'target_date': sp.target_date.isoformat(),
                'problems_per_day': sp.problems_per_day,
                'is_active': sp.is_active,
                'created_at': sp.created_at.isoformat(),
                'days': [
                    {
                        'date': d.date.isoformat(),
                        'focus_topic': d.focus_topic,
                        'difficulty_target': d.difficulty_target,
                        'reason': d.reason,
                        'problems': [
                            {
                                'id': str(p.id),
                                'title': p.title,
                                'slug': p.slug,
                                'difficulty': p.difficulty,
                            }
                            for p in d.problems.all()
                        ],
                    }
                    for d in sp.days.all().order_by('date')
                ],
            }
            for sp in study_plans
        ],
    }


def export_user_progress_csv(user):
    """
    Export user problem progress as CSV string.

    Columns: problem_id, title, difficulty, status, current_box, next_review_date,
    times_solved, times_attempted, last_solved, notes, code_solution
    """
    progresses = UserProblemProgress.objects.filter(user=user).select_related('problem').prefetch_related('problem__tags', 'problem__companies')

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'problem_id', 'title', 'slug', 'difficulty', 'tags', 'companies',
        'source_url', 'status', 'current_box', 'next_review_date',
        'times_solved', 'times_attempted', 'last_attempted', 'last_solved',
        'notes', 'code_solution', 'reviews_count', 'created_at', 'updated_at'
    ])

    for p in progresses:
        writer.writerow([
            str(p.problem.id),
            p.problem.title,
            p.problem.slug,
            p.problem.difficulty,
            '|'.join([t.name for t in p.problem.tags.all()]),
            '|'.join([c.name for c in p.problem.companies.all()]),
            p.problem.source_url,
            p.status,
            p.current_box,
            p.next_review_date.isoformat() if p.next_review_date else '',
            p.times_solved,
            p.times_attempted,
            p.last_attempted.isoformat() if p.last_attempted else '',
            p.last_solved.isoformat() if p.last_solved else '',
            p.notes,
            p.code_solution,
            p.reviews_count,
            p.created_at.isoformat(),
            p.updated_at.isoformat(),
        ])

    return output.getvalue()


def export_user_progress_markdown(user):
    """
    Export user progress as human-readable Markdown.
    """
    progresses = UserProblemProgress.objects.filter(user=user).select_related('problem').prefetch_related('problem__tags', 'problem__companies')
    streak = UserStreak.objects.filter(user=user).first()

    # Group by status
    by_status = {
        'SOLVED': [],
        'NEEDS_REVISIT': [],
        'UNSOLVED': [],
        'SKIPPED': [],
    }
    for p in progresses:
        by_status[p.status].append(p)

    lines = []
    lines.append(f"# DSA Tracker Progress Export for {user.username}")
    lines.append(f"*Exported on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")
    lines.append("")

    # Streak info
    if streak:
        lines.append(f"## 🔥 Streaks")
        lines.append(f"- **Current Streak:** {streak.current_streak} days")
        lines.append(f"- **Longest Streak:** {streak.longest_streak} days")
        if streak.last_solved_date:
            lines.append(f"- **Last Solved:** {streak.last_solved_date}")
        lines.append("")

    # Summary
    total = sum(len(v) for v in by_status.values())
    lines.append(f"## 📊 Summary")
    lines.append(f"- **Total Problems Tracked:** {total}")
    lines.append(f"- **Solved:** {len(by_status['SOLVED'])}")
    lines.append(f"- **Needs Revisit:** {len(by_status['NEEDS_REVISIT'])}")
    lines.append(f"- **Skipped:** {len(by_status['SKIPPED'])}")
    lines.append(f"- **Unsolved:** {len(by_status['UNSOLVED'])}")
    lines.append("")

    # Problems by status
    status_emojis = {
        'SOLVED': '✅',
        'NEEDS_REVISIT': '🔄',
        'UNSOLVED': '⏳',
        'SKIPPED': '⏭️',
    }

    for status, items in by_status.items():
        if not items:
            continue
        lines.append(f"## {status_emojis.get(status, '')} {status} ({len(items)})")
        lines.append("")

        for p in items:
            problem = p.problem
            lines.append(f"### {problem.title} ({problem.difficulty})")
            lines.append(f"- **Link:** {problem.source_url}")
            if problem.tags.exists():
                tags = ', '.join([t.name for t in problem.tags.all()])
                lines.append(f"- **Topics:** {tags}")
            if problem.companies.exists():
                companies = ', '.join([c.name for c in problem.companies.all()])
                lines.append(f"- **Companies:** {companies}")
            lines.append(f"- **Leitner Box:** {p.current_box}/5")
            if p.next_review_date:
                lines.append(f"- **Next Review:** {p.next_review_date.strftime('%Y-%m-%d')}")
            lines.append(f"- **Times Solved:** {p.times_solved}")
            lines.append(f"- **Times Attempted:** {p.times_attempted}")
            if p.last_solved:
                lines.append(f"- **Last Solved:** {p.last_solved.strftime('%Y-%m-%d')}")
            if p.notes:
                lines.append(f"- **Notes:** {p.notes}")
            if p.code_solution:
                lines.append(f"- **Code Solution:**")
                lines.append(f"```python")
                lines.append(p.code_solution)
                lines.append(f"```")
            lines.append("")

    return '\n'.join(lines)


def get_export_response(data, format='json', filename='dsa_tracker_export'):
    """
    Create an HttpResponse with the exported data.
    """
    from django.http import HttpResponse

    if format == 'json':
        return HttpResponse(
            json.dumps(data, indent=2),
            content_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{filename}.json"'}
        )
    elif format == 'csv':
        return HttpResponse(
            data,
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}.csv"'}
        )
    elif format == 'markdown':
        return HttpResponse(
            data,
            content_type='text/markdown',
            headers={'Content-Disposition': f'attachment; filename="{filename}.md"'}
        )
    else:
        raise ValueError(f"Unknown format: {format}")