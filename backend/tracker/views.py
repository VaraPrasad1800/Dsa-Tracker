from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q, Case, When
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import ValidationError as DjangoValidationError

from tracker.models import (
    Tag, Company, Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay, UserProfile, Solution
)
from tracker.serializers import (
    TagSerializer, CompanySerializer, ProblemSerializer,
    UserProblemProgressSerializer, ReviewHistorySerializer,
    StudyPlanSerializer, BookmarkedProblemSerializer, SolutionSerializer
)
from tracker.scraper import fetch_solution
from tracker.services.leitner import update_problem_progress, get_leitner_box_stats
from tracker.services.analytics import (
    get_user_heatmap, get_user_topic_breakdown, get_user_streaks,
    get_user_difficulty_breakdown, get_user_timeline, get_user_dashboard
)
from tracker.services.study_plan import generate_study_plan, get_study_plan_progress
from tracker.services.reminders import get_or_create_daily_review_digest
from tracker.services.export import (
    export_user_progress_json,
    export_user_progress_csv,
    export_user_progress_markdown,
    get_export_response
)
from tracker.authentication import generate_jwt_token, generate_jwt_tokens
from tracker.services.email_service import (
    send_verification_email,
    send_password_reset_email,
)
from tracker.services.auth_tokens import (
    generate_auth_token,
    hash_token,
    is_token_expired,
    create_verification_token,
    create_password_reset_token,
    get_verification_expiry_hours,
    get_password_reset_expiry_hours,
)

User = get_user_model()


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


# Auth-token helpers (generate_auth_token, hash_token, is_token_expired,
# create_*_token, get_*_expiry_hours) are imported from tracker.services.auth_tokens.

def get_request_user(request):
    """
    Return the authenticated user for the request.
    With demo-mode removed, all protected endpoints require a valid JWT/Token/Session.
    The request may be anonymous (e.g. public problem browsing), in which case None is returned.
    """
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return request.user
    return None

class ProblemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProblemListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = get_request_user(request)
        queryset = Problem.objects.all().prefetch_related('tags', 'companies')

        def multi_values(param):
            """Return a cleaned list for comma-separated or repeated param values."""
            raw = request.query_params.getlist(param)
            vals = []
            for item in raw:
                vals.extend(v for v in item.split(',') if v.strip())
            return list(dict.fromkeys(v.strip() for v in vals if v.strip()))  # dedupe, preserve order

        # Multi-select difficulty: ?difficulty=Easy,Hard or ?difficulty=Easy&difficulty=Hard
        difficulties = multi_values('difficulty')
        if difficulties:
            queryset = queryset.filter(difficulty__in=[d.capitalize() for d in difficulties])

        # Multi-select tags: matched by slug or name
        tags = multi_values('tags') or multi_values('topic')
        if tags:
            q = Q()
            for t in tags:
                q |= Q(tags__slug__iexact=t) | Q(tags__name__iexact=t)
            queryset = queryset.filter(q)

        # Multi-select company: matched by slug or name
        companies = multi_values('company')
        if companies:
            q = Q()
            for c in companies:
                q |= Q(companies__slug__iexact=c) | Q(companies__name__iexact=c)
            queryset = queryset.filter(q)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(tags__name__icontains=search) |
                Q(companies__name__icontains=search)
            )

        # Multi-select status (requires a logged-in user for per-user progress)
        status_filters = multi_values('status')
        if status_filters and user:
            for status_filter in status_filters:
                if status_filter.upper() == 'UNSOLVED':
                    solved_or_revisit_ids = UserProblemProgress.objects.filter(
                        user=user, status__in=['SOLVED', 'NEEDS_REVISIT', 'SKIPPED']
                    ).values_list('problem_id', flat=True)
                    queryset = queryset.exclude(id__in=solved_or_revisit_ids)
                else:
                    target_ids = UserProblemProgress.objects.filter(
                        user=user, status=status_filter.upper()
                    ).values_list('problem_id', flat=True)
                    queryset = queryset.filter(id__in=target_ids)

        # Bookmark filter: ?bookmarked=true restricts to the user's bookmarks
        if request.query_params.get('bookmarked') == 'true' and user:
            queryset = queryset.filter(bookmarked_by=user)

        # Random mode: no company selected, homepage shows a shuffled sample.
        # ?sort=random or ?random=true returns a randomized set.
        random_mode = request.query_params.get('random') == 'true' or request.query_params.get('sort') == 'random'
        if random_mode:
            queryset = queryset.order_by('?')
        else:
            # Sorting: added date (newest first default is fine), last updated, frequency, difficulty
            sort = request.query_params.get('sort')
            order_map = {
                'frequency': '-frequency',
                'created': '-created_at',
                'updated': '-updated_at',
                'difficulty_asc': 'difficulty',
                'difficulty_desc': '-difficulty',
                'title': 'title',
                'frequency_asc': 'frequency',
            }
            order_field = order_map.get(sort, 'title')
            queryset = queryset.distinct().order_by(order_field)

        # Filter counts summary for pills
        all_problems = Problem.objects.all()
        user_progresses = UserProblemProgress.objects.filter(user=user) if user else UserProblemProgress.objects.none()
        solved_count = user_progresses.filter(status='SOLVED').count()
        revisit_count = user_progresses.filter(status='NEEDS_REVISIT').count()
        skipped_count = user_progresses.filter(status='SKIPPED').count()
        total_count = all_problems.count()
        unsolved_count = max(0, total_count - (solved_count + revisit_count + skipped_count))

        filter_counts = {
            'total': total_count,
            'easy': all_problems.filter(difficulty='Easy').count(),
            'medium': all_problems.filter(difficulty='Medium').count(),
            'hard': all_problems.filter(difficulty='Hard').count(),
            'solved': solved_count,
            'unsolved': unsolved_count,
            'needs_revisit': revisit_count,
            'skipped': skipped_count,
            'bookmarked': (
                UserProfile.objects.filter(user=user).values('bookmarked_problems').count() if user else 0
            ),
        }

        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProblemSerializer(page, many=True, context={'request': request})
        response = paginator.get_paginated_response(serializer.data)
        response.data['counts'] = filter_counts
        return response

class ProblemDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            problem = Problem.objects.prefetch_related('tags', 'companies').get(pk=pk)
        except Problem.DoesNotExist:
            return Response({'error': 'Problem not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProblemSerializer(problem, context={'request': request})
        return Response(serializer.data)

class ProblemSolutionView(APIView):
    """
    Return a cached (and, if stale, freshly scraped) solution for a problem.

    GET /api/problems/<uuid>/solution/
    - Authenticated.
    - If the problem has no leetcode_id, returns 404.
    - Uses the Solution cache (7-day freshness). On a cache miss / stale entry
      it tries a live fetch via tracker.scraper.fetch_solution and updates
      the cache. Never proxies raw HTML to the client.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            problem = Problem.objects.get(pk=pk)
        except Problem.DoesNotExist:
            return Response({'available': False, 'message': 'Problem not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if not problem.leetcode_id:
            return Response({'available': False, 'message': 'No LeetCode ID for this problem; solution unavailable.'},
                            status=status.HTTP_404_NOT_FOUND)

        cached = None
        try:
            cached = Solution.objects.get(problem=problem)
        except Solution.DoesNotExist:
            cached = None

        # Serve fresh successful cache directly — skip fetch entirely
        if cached and cached.is_fresh:
            return Response({
                'available': True,
                'question_number': cached.question_number or problem.leetcode_id,
                'title': cached.title,
                'description': cached.description or problem.description,
                'code': cached.code,
                'language': cached.language,
                'explanation': cached.explanation,
                'solution': cached.explanation,
                'time_complexity': cached.time_complexity,
                'space_complexity': cached.space_complexity,
                'source_url': cached.source_url,
                'solution_source_url': cached.solution_source_url,
            })

        # If a failed record exists but was attempted recently, don't hammer upstream again.
        # should_retry_failed is True only after 1 hour since the last failure.
        if cached and cached.fetch_failed and not cached.should_retry_failed:
            return Response(
                {'available': False, 'message': 'Solution temporarily unavailable. Please try again later.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Cache miss / stale / ready-to-retry — perform a live fetch
        fetched = fetch_solution(problem.leetcode_id)

        if fetched:
            desc = fetched.get('description') or problem.description or ''
            if desc and not problem.description:
                problem.description = desc
                problem.save(update_fields=['description'])

            sol, _ = Solution.objects.update_or_create(
                problem=problem,
                defaults={
                    'question_number': fetched.get('question_number') or problem.leetcode_id,
                    'title': fetched.get('title') or problem.title,
                    'description': desc,
                    'code': fetched.get('code') or '# Solution not available',
                    'language': fetched.get('language') or 'python',
                    'explanation': fetched.get('explanation') or '',
                    'time_complexity': fetched.get('time_complexity') or '',
                    'space_complexity': fetched.get('space_complexity') or '',
                    'source_url': fetched.get('source_url') or f'https://leetcode.ca/all/{problem.leetcode_id}.html',
                    'solution_source_url': fetched.get('solution_source_url') or '',
                    'fetch_failed': False,
                    'fetch_error': '',
                },
            )
            return Response({
                'available': True,
                'question_number': sol.question_number or problem.leetcode_id,
                'title': sol.title,
                'description': sol.description,
                'code': sol.code,
                'language': sol.language,
                'explanation': sol.explanation,
                'solution': sol.explanation,
                'time_complexity': sol.time_complexity,
                'space_complexity': sol.space_complexity,
                'source_url': sol.source_url,
                'solution_source_url': sol.solution_source_url,
            })

        # Fetch failed — record failure (allows retry after 1 hour via should_retry_failed)
        err_msg = 'Upstream fetch failed or returned no content.'
        if cached:
            cached.fetch_failed = True
            cached.fetch_error = err_msg
            cached.save(update_fields=['fetch_failed', 'fetch_error', 'last_fetched_at'])
        else:
            # Create a stub failure record so we rate-limit retry attempts
            Solution.objects.create(
                problem=problem,
                question_number=problem.leetcode_id,
                title=problem.title,
                description='',
                code='',
                language='python',
                explanation='',
                source_url=f'https://leetcode.ca/all/{problem.leetcode_id}.html',
                solution_source_url='',
                fetch_failed=True,
                fetch_error=err_msg,
            )

        return Response(
            {'available': False, 'message': 'Solution temporarily unavailable. Please try again later.'},
            status=status.HTTP_404_NOT_FOUND,
        )


class TagListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tags = Tag.objects.annotate(problem_count=Count('problems')).order_by('name')
        serializer = TagSerializer(tags, many=True, context={'request': request})
        return Response(serializer.data)

class ProblemByCompanyView(APIView):
    """
    Drill into problems for a single company.

    GET /api/problems/by-company/<company_id>/?difficulty=easy&status=solved&tags=...&sort=frequency&random=true
    company_id may be a slug or a UUID.
    """
    permission_classes = [AllowAny]

    def get(self, request, company_id):
        # Resolve the company by slug or id
        company = None
        try:
            # Try slug first (company grid routes use slugs: /problems/company/{company_slug})
            company = Company.objects.get(slug=company_id)
        except (Company.DoesNotExist, Exception):
            try:
                company = Company.objects.get(pk=company_id)
            except Exception:
                return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

        queryset = Problem.objects.filter(companies=company).prefetch_related('tags', 'companies')

        def multi_values(param):
            raw = request.query_params.getlist(param)
            vals = []
            for item in raw:
                vals.extend(v for v in item.split(',') if v.strip())
            return list(dict.fromkeys(v.strip() for v in vals if v.strip()))

        difficulties = multi_values('difficulty')
        if difficulties:
            queryset = queryset.filter(difficulty__in=[d.capitalize() for d in difficulties])

        tags = multi_values('tags') or multi_values('topic')
        if tags:
            q = Q()
            for t in tags:
                q |= Q(tags__slug__iexact=t) | Q(tags__name__iexact=t)
            queryset = queryset.filter(q)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(tags__name__icontains=search)
            )

        status_filters = multi_values('status')
        user = get_request_user(request)
        if status_filters and user:
            for status_filter in status_filters:
                if status_filter.upper() == 'UNSOLVED':
                    solved_or_revisit_ids = UserProblemProgress.objects.filter(
                        user=user, status__in=['SOLVED', 'NEEDS_REVISIT', 'SKIPPED']
                    ).values_list('problem_id', flat=True)
                    queryset = queryset.exclude(id__in=solved_or_revisit_ids)
                else:
                    target_ids = UserProblemProgress.objects.filter(
                        user=user, status=status_filter.upper()
                    ).values_list('problem_id', flat=True)
                    queryset = queryset.filter(id__in=target_ids)

        # Bookmark filter: ?bookmarked=true restricts to the user's bookmarks
        if request.query_params.get('bookmarked') == 'true' and user:
            queryset = queryset.filter(bookmarked_by=user)

        random_mode = request.query_params.get('random') == 'true' or request.query_params.get('sort') == 'random'
        if random_mode:
            queryset = queryset.order_by('?')
        else:
            sort = request.query_params.get('sort')
            order_map = {
                'frequency': '-frequency',
                'created': '-created_at',
                'updated': '-updated_at',
                'title': 'title',
                'frequency_asc': 'frequency',
            }
            order_field = order_map.get(sort, '-frequency')
            queryset = queryset.distinct().order_by(order_field)

        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProblemSerializer(page, many=True, context={'request': request})
        response = paginator.get_paginated_response(serializer.data)
        response.data['company'] = CompanySerializer(company).data
        return response


class CompanyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        companies = Company.objects.annotate(problem_count=Count('problems')).order_by('name')
        serializer = CompanySerializer(companies, many=True, context={'request': request})
        return Response(serializer.data)

class UserProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = get_request_user(request)
        problem_id = request.data.get('problem_id')
        new_status = request.data.get('status', 'SOLVED')
        notes = request.data.get('notes')
        code_solution = request.data.get('code_solution')
        time_spent = int(request.data.get('time_spent_minutes', 0))

        if not problem_id:
            return Response({'error': 'problem_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return Response({'error': 'Problem not found'}, status=status.HTTP_404_NOT_FOUND)

        progress = update_problem_progress(
            user=user,
            problem=problem,
            status=new_status,
            notes=notes,
            code_solution=code_solution,
            time_spent_minutes=time_spent
        )
        return Response(UserProblemProgressSerializer(progress).data, status=status.HTTP_200_OK)

class UserProgressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = get_request_user(request)
        try:
            progress = UserProblemProgress.objects.get(pk=pk, user=user)
        except UserProblemProgress.DoesNotExist:
            return Response({'error': 'Progress record not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status', progress.status)
        notes = request.data.get('notes', progress.notes)
        code_solution = request.data.get('code_solution', progress.code_solution)
        time_spent = int(request.data.get('time_spent_minutes', 0))

        progress = update_problem_progress(
            user=user,
            problem=progress.problem,
            status=new_status,
            notes=notes,
            code_solution=code_solution,
            time_spent_minutes=time_spent
        )
        return Response(UserProblemProgressSerializer(progress).data)

class UserProgressStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        total_problems = Problem.objects.count()
        progresses = UserProblemProgress.objects.filter(user=user)
        total_solved = progresses.filter(status='SOLVED').count()
        total_attempted = progresses.filter(times_attempted__gt=0).count()
        total_revisit = progresses.filter(status='NEEDS_REVISIT').count()

        box_stats = get_leitner_box_stats(user)
        streak_data = get_user_streaks(user)
        topic_data = get_user_topic_breakdown(user)
        weak_topics = [t['name'] for t in topic_data['topics'] if t['is_weak']][:5]

        return Response({
            'total_problems': total_problems,
            'total_solved': total_solved,
            'total_attempted': total_attempted,
            'total_revisit': total_revisit,
            'current_streak': streak_data['current_streak'],
            'longest_streak': streak_data['longest_streak'],
            'due_today_count': box_stats['due_today_count'],
            'weak_topics': weak_topics,
        })

# Phase 2 Spaced Repetition Endpoints
class DueTodayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        now = timezone.now()
        due_progresses = UserProblemProgress.objects.filter(
            user=user,
            next_review_date__lte=now
        ).select_related('problem').prefetch_related('problem__tags', 'problem__companies').order_by('current_box', 'last_attempted')

        results = []
        for p in due_progresses:
            prob_data = ProblemSerializer(p.problem, context={'request': request}).data
            results.append({
                'progress_id': p.id,
                'current_box': p.current_box,
                'next_review_date': p.next_review_date,
                'times_solved': p.times_solved,
                'times_attempted': p.times_attempted,
                'notes': p.notes,
                'code_solution': p.code_solution,
                'problem': prob_data
            })
        return Response(results)

class SpacedRepetitionStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        stats = get_leitner_box_stats(user)
        return Response(stats)

class UserProgressHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_request_user(request)
        try:
            progress = UserProblemProgress.objects.get(pk=pk, user=user)
        except UserProblemProgress.DoesNotExist:
            return Response({'error': 'Progress not found'}, status=status.HTTP_404_NOT_FOUND)

        histories = ReviewHistory.objects.filter(progress=progress).order_by('created_at')
        box_transitions = [
            {
                'old_box': h.old_box,
                'new_box': h.new_box,
                'action': h.action,
                'date': h.created_at.strftime('%Y-%m-%d %H:%M')
            }
            for h in histories
        ]
        review_dates = [h.created_at.strftime('%Y-%m-%d') for h in histories]

        return Response({
            'problem_id': progress.problem.id,
            'problem_title': progress.problem.title,
            'current_box': progress.current_box,
            'box_transitions': box_transitions,
            'review_dates': review_dates,
            'times_solved': progress.times_solved,
            'reviews_count': progress.reviews_count,
        })

# Phase 3 Analytics Endpoints
class HeatmapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        year = request.query_params.get('year')
        year = int(year) if year and year.isdigit() else timezone.now().year
        data = get_user_heatmap(user, year)
        return Response(data)

class TopicBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        data = get_user_topic_breakdown(user)
        return Response(data)

class StreaksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        data = get_user_streaks(user)
        return Response(data)

class DifficultyBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        data = get_user_difficulty_breakdown(user)
        return Response(data)

class TimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        days = request.query_params.get('days', '90')
        days = int(days) if days.isdigit() else 90
        data = get_user_timeline(user, days)
        return Response(data)

# Phase 4 Reminders Endpoint
class DailyDigestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        digest = get_or_create_daily_review_digest(user)
        return Response(digest)

# Phase 5 Study Plan Endpoints
class StudyPlanGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = get_request_user(request)
        target_date_str = request.data.get('target_date') or request.data.get('date')
        # Daily goal: 10/15/20 problems per day (default 10 when days-based plan requested)
        problems_per_day = int(request.data.get('problems_per_day', request.data.get('daily_goal', 10)))
        # Duration in days; if target_date absent, compute it from `days` (default 30-day plan).
        days = int(request.data.get('days', 30))

        if target_date_str:
            try:
                target_date = timezone.datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.now().date() + timedelta(days=days)

        plan = generate_study_plan(user, target_date, problems_per_day)
        serializer = StudyPlanSerializer(plan, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class StudyPlanActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        plan = StudyPlan.objects.filter(user=user, is_active=True).first()
        if not plan:
            return Response({'active_plan': None})

        serializer = StudyPlanSerializer(plan, context={'request': request})
        progress = get_study_plan_progress(plan, user)
        return Response({
            'active_plan': serializer.data,
            'progress': progress
        })

class StudyPlanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_request_user(request)
        try:
            plan = StudyPlan.objects.get(pk=pk, user=user)
        except StudyPlan.DoesNotExist:
            return Response({'error': 'Study plan not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudyPlanSerializer(plan, context={'request': request})
        progress = get_study_plan_progress(plan, user)
        return Response({
            'plan': serializer.data,
            'progress': progress
        })

class StudyPlanDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = get_request_user(request)
        try:
            plan = StudyPlan.objects.get(pk=pk, user=user)
        except StudyPlan.DoesNotExist:
            return Response({'error': 'Study plan not found'}, status=status.HTTP_404_NOT_FOUND)

        plan.is_active = False
        plan.save()
        return Response({'message': 'Plan archived successfully', 'plan_id': plan.id})

class StudyPlanProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_request_user(request)
        try:
            plan = StudyPlan.objects.get(pk=pk, user=user)
        except StudyPlan.DoesNotExist:
            return Response({'error': 'Study plan not found'}, status=status.HTTP_404_NOT_FOUND)

        progress = get_study_plan_progress(plan, user)
        return Response(progress)

# Demo Authentication & User Switcher
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = get_or_create_profile(user)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_email_verified': profile.is_email_verified,
        })


# JWT Authentication Views
class RegisterView(APIView):
    """
    Register a new user and send an email verification link.

    POST /api/auth/signup/
    Body: { "username", "email", "password" }
    Returns: { "user": {...} } + sends verification email. User is inactive until verified.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        # Validation
        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(username) < 3:
            return Response({'error': 'Username must be at least 3 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({'error': 'Email is required to create an account.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'An account with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate password using Django's validators
        try:
            validate_password(password, User(username=username, email=email))
        except DjangoValidationError as e:
            return Response({'error': e.messages[0] if e.messages else 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user (inactive until email verified) + profile
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True,  # email verification gates LOGIN below, not account creation
        )
        profile = get_or_create_profile(user)
        profile.is_email_verified = False

        # Generate + store (hashed) verification token
        token = generate_auth_token()
        profile.email_verification_token_hash = hash_token(token)
        profile.email_verification_sent_at = timezone.now()
        profile.save()

        # Send verification email (SendGrid in prod, console fallback in dev)
        sent = send_verification_email(user, token)

        return Response({
            'message': 'Account created. Please check your email to verify your account.',
            'verification_email_sent': bool(sent),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_email_verified': False,
            },
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Authenticate user and return JWT tokens (access + refresh).

    POST /api/auth/login/
    Body: { "username" or "email": str, "password": str }
    Supports username or email in the `username` field.
    Requires email verification unless the account was created before verification was enforced.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = (request.data.get('username') or request.data.get('email') or '').strip()
        password = request.data.get('password', '')

        if not identifier:
            return Response({'error': 'Username or email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Look up by username or email (identifier field is aliased to username in the spec)
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                return Response({'error': 'Invalid username/email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'error': 'Account is disabled. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
        if not user.check_password(password):
            return Response({'error': 'Invalid username/email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Gate on email verification when the user's email was collected
        if user.email:
            profile = get_or_create_profile(user)
            if not profile.is_email_verified:
                # Accounts created before this change (seed users) are treated as verified
                is_seed_user = user.username in ('demo_user', 'test_user')
                if not is_seed_user:
                    return Response({
                        'error': 'Please verify your email before logging in.',
                        'code': 'email_not_verified',
                        'email': user.email,
                    }, status=status.HTTP_403_FORBIDDEN)

        tokens = generate_jwt_tokens(user)
        drf_token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Login successful.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'access_token': tokens['access'],
            'refresh_token': tokens['refresh'],
            'jwt_token': tokens['access'],
            'token': drf_token.key,
        }, status=status.HTTP_200_OK)


class VerifyTokenView(APIView):
    """Verify if a JWT token is valid and return user info."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = get_or_create_profile(user)
        return Response({
            'valid': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_email_verified': profile.is_email_verified,
            },
            'message': 'Token is valid.',
        })


class VerifyEmailView(APIView):
    """Verify a user's email via token from verification link.

    POST /api/auth/verify-email/
    Body: { "token": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hash_token(token)
        try:
            profile = UserProfile.objects.select_related('user').get(email_verification_token_hash=token_hash)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Invalid or expired verification token.'}, status=status.HTTP_400_BAD_REQUEST)

        if is_token_expired(profile.email_verification_sent_at, getattr(settings, 'EMAIL_VERIFICATION_EXPIRY_HOURS', 24)):
            return Response({'error': 'Verification link expired. Please request a new one.', 'code': 'expired'},
                            status=status.HTTP_400_BAD_REQUEST)

        profile.is_email_verified = True
        profile.email_verification_token_hash = ''
        profile.email_verification_sent_at = None
        profile.save()

        return Response({'message': 'Email verified successfully. You can now log in.',
                         'user': {'id': profile.user.id, 'username': profile.user.username,
                                  'email': profile.user.email, 'is_email_verified': True}}, status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    """Resend email verification for an unverified account.

    POST /api/auth/resend-verification/
    Body: { "email": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Always succeed to avoid email enumeration
            return Response({'message': 'If an account with that email exists, a verification email has been sent.'})

        profile = get_or_create_profile(user)
        if profile.is_email_verified:
            return Response({'message': 'Email already verified. Please log in.'})

        token = generate_auth_token()
        profile.email_verification_token_hash = hash_token(token)
        profile.email_verification_sent_at = timezone.now()
        profile.save()
        sent = send_verification_email(user, token)
        return Response({'message': 'Verification email sent.', 'verification_email_sent': bool(sent)})


class ForgotPasswordView(APIView):
    """Request a password reset email.

    POST /api/auth/forgot-password/
    Body: { "email": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Always succeed to avoid email enumeration
        message = {'message': 'If an account with that email exists, a password reset link has been sent.'}

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(message)

        profile = get_or_create_profile(user)
        token = generate_auth_token()
        profile.password_reset_token_hash = hash_token(token)
        profile.password_reset_sent_at = timezone.now()
        profile.save()

        send_password_reset_email(user, token)
        return Response(message)


class ResetPasswordView(APIView):
    """Reset a user's password using a token from the reset link.

    POST /api/auth/reset-password/
    Body: { "token": "string", "new_password": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        new_password = (request.data.get('new_password') or '').strip()

        if not token:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'New password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hash_token(token)
        try:
            profile = UserProfile.objects.select_related('user').get(password_reset_token_hash=token_hash)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Invalid or expired reset token.'}, status=status.HTTP_400_BAD_REQUEST)

        if is_token_expired(profile.password_reset_sent_at, getattr(settings, 'PASSWORD_RESET_EXPIRY_HOURS', 24)):
            return Response({'error': 'Reset link expired. Please request a new one.', 'code': 'expired'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = profile.user
        user.set_password(new_password)
        user.save()

        profile.password_reset_token_hash = ''
        profile.password_reset_sent_at = None
        profile.save()

        return Response({'message': 'Password reset successful. You can now log in with your new password.'})


class RefreshTokenView(APIView):
    """Refresh an access token using a valid refresh token.

    POST /api/auth/refresh-token/
    Body: { "refresh_token": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = (request.data.get('refresh_token') or '').strip()
        if not refresh_token:
            return Response({'error': 'refresh_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from tracker.authentication import decode_jwt_token
            payload = decode_jwt_token(refresh_token)
        except Exception:
            return Response({'error': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get('token_type') != 'refresh':
            return Response({'error': 'Invalid token type: expected a refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=payload.get('user_id'))
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)

        tokens = generate_jwt_tokens(user)
        return Response({
            'access_token': tokens['access'],
            'refresh_token': tokens['refresh'],
        })


# Export Progress Endpoint
class ExportProgressView(APIView):
    """
    Export user progress data in various formats.

    GET /api/export/progress/?format=json|csv|markdown
    Returns: Attachment file with user's progress data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        format = request.query_params.get('format', 'json')

        if format == 'json':
            data = export_user_progress_json(user)
            return get_export_response(data, format='json', filename=f'{user.username}_dsa_tracker_export')
        elif format == 'csv':
            data = export_user_progress_csv(user)
            return get_export_response(data, format='csv', filename=f'{user.username}_dsa_tracker_export')
        elif format == 'markdown':
            data = export_user_progress_markdown(user)
            return get_export_response(data, format='markdown', filename=f'{user.username}_dsa_tracker_export')
        else:
            return Response({'error': 'Invalid format. Use json, csv, or markdown.'}, status=status.HTTP_400_BAD_REQUEST)


# Bookmark Endpoints
class BookmarkToggleView(APIView):
    """
    Toggle a problem's bookmark status for the authenticated user.

    POST /api/bookmarks/toggle/
    Body: { "problem_id": "<uuid>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        problem_id = request.data.get('problem_id')
        if not problem_id:
            return Response({'error': 'problem_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return Response({'error': 'Problem not found'}, status=status.HTTP_404_NOT_FOUND)

        profile = get_or_create_profile(request.user)
        if profile.bookmarked_problems.filter(pk=problem.pk).exists():
            profile.bookmarked_problems.remove(problem)
            return Response({'bookmarked': False, 'message': 'Bookmark removed'})
        else:
            profile.bookmarked_problems.add(problem)
            return Response({'bookmarked': True, 'message': 'Bookmark added'})


class BookmarkListView(APIView):
    """
    List all bookmarked problems for the authenticated user with progress data.

    GET /api/bookmarks/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        bookmarks = profile.bookmarked_problems.all().prefetch_related('tags', 'companies')
        serializer = BookmarkedProblemSerializer(bookmarks, many=True, context={'request': request})
        return Response(serializer.data)


# Analytics Dashboard Endpoint
class AnalyticsDashboardView(APIView):
    """
    Get the full analytics dashboard summary for the authenticated user.

    GET /api/analytics/dashboard/
    Returns: Placement readiness dashboard with all metrics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dashboard = get_user_dashboard(request.user)
        return Response(dashboard)
