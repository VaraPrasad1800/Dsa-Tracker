import logging
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

logger = logging.getLogger(__name__)

from tracker.models import (
    Tag, Company, Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay, UserProfile, Solution,
    Submission, Challenge, Achievement, Notification, InterviewSession,
    InterviewProblem, DSAPattern, TestCase, UserPoints, RefreshToken,
)
from tracker.serializers import (
    TagSerializer, CompanySerializer, ProblemSerializer, ProblemListSerializer,
    UserProblemProgressSerializer, ReviewHistorySerializer,
    StudyPlanSerializer, BookmarkedProblemSerializer, SolutionSerializer,
    SubmissionSerializer, SubmissionDetailSerializer,
    ChallengeSerializer, AchievementSerializer, NotificationSerializer,
    InterviewSessionSerializer, DSAPatternSerializer, TestCaseSerializer,
    UserPointsSerializer,
)
from tracker.scraper import fetch_solution
from tracker.services.leitner import update_problem_progress, get_leitner_box_stats
from tracker.services.analytics import (
    get_user_heatmap, get_user_topic_breakdown, get_user_streaks,
    get_user_difficulty_breakdown, get_user_timeline, get_user_dashboard,
    get_topic_mastery_levels, get_revision_queue, get_company_track,
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
from tracker.throttles import JudgeRunThrottle, JudgeSubmitThrottle
from drf_spectacular.utils import extend_schema, OpenApiResponse

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

    @extend_schema(
        summary="List problems",
        description="Paginated list of problems with filtering, search, and practice status.",
        responses={200: ProblemListSerializer(many=True)},
    )
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

        search = request.query_params.get('search', '')
        exact_number_match = None
        if search:
            search = search.strip()
            search_query = (
                Q(title__icontains=search) |
                Q(tags__name__icontains=search) |
                Q(companies__name__icontains=search)
            )
            clean_search = search.lstrip('#').strip()
            if clean_search.isdigit():
                q_num = int(clean_search)
                search_query |= Q(question_number=q_num)
                exact_number_match = q_num
            queryset = queryset.filter(search_query)

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

        # Enforce distinct to eliminate Many-to-Many row duplication from tags/companies joins
        queryset = queryset.distinct()

        # Random mode: no company selected, homepage shows a shuffled sample.
        # ?sort=random or ?random=true returns a randomized set.
        random_mode = request.query_params.get('random') == 'true' or request.query_params.get('sort') == 'random'
        if random_mode:
            queryset = queryset.order_by('?')
        else:
            # Deterministic sorting with question_number tie-breaker for stable pagination
            sort = request.query_params.get('sort')
            order_map = {
                'number': ('question_number',),
                'number_desc': ('-question_number',),
                'question_number': ('question_number',),
                '-question_number': ('-question_number',),
                'frequency': ('-frequency', 'question_number'),
                'frequency_asc': ('frequency', 'question_number'),
                'created': ('-created_at', 'question_number'),
                'updated': ('-updated_at', 'question_number'),
                'difficulty_asc': ('difficulty', 'question_number'),
                'difficulty_desc': ('-difficulty', 'question_number'),
                'title': ('title', 'question_number'),
            }
            order_fields = order_map.get(sort, ('question_number',))
            if exact_number_match is not None:
                queryset = queryset.order_by(
                    Case(When(question_number=exact_number_match, then=0), default=1),
                    *order_fields
                )
            else:
                queryset = queryset.order_by(*order_fields)

        # Filter counts summary for pills — single-query aggregation
        counts_agg = Problem.objects.aggregate(
            total=Count('id'),
            easy=Count('id', filter=Q(difficulty='Easy')),
            medium=Count('id', filter=Q(difficulty='Medium')),
            hard=Count('id', filter=Q(difficulty='Hard')),
        )
        total_count = counts_agg['total'] or 0

        if user:
            prog_agg = UserProblemProgress.objects.filter(user=user).aggregate(
                solved=Count('id', filter=Q(status='SOLVED')),
                needs_revisit=Count('id', filter=Q(status='NEEDS_REVISIT')),
                skipped=Count('id', filter=Q(status='SKIPPED')),
            )
            solved_count = prog_agg['solved'] or 0
            revisit_count = prog_agg['needs_revisit'] or 0
            skipped_count = prog_agg['skipped'] or 0
            user_profile = getattr(user, 'profile', None) or UserProfile.objects.filter(user=user).first()
            bookmarked_count = user_profile.bookmarked_problems.count() if user_profile else 0
        else:
            user_profile = None
            solved_count = 0
            revisit_count = 0
            skipped_count = 0
            bookmarked_count = 0

        unsolved_count = max(0, total_count - (solved_count + revisit_count + skipped_count))

        filter_counts = {
            'total': total_count,
            'easy': counts_agg['easy'] or 0,
            'medium': counts_agg['medium'] or 0,
            'hard': counts_agg['hard'] or 0,
            'solved': solved_count,
            'unsolved': unsolved_count,
            'needs_revisit': revisit_count,
            'skipped': skipped_count,
            'bookmarked': bookmarked_count,
        }

        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)

        # Batch preload user progress and bookmarks for this page to eliminate N+1 queries
        if user and page:
            page_problem_ids = [p.id for p in page]
            user_progress_map = {
                up.problem_id: up
                for up in UserProblemProgress.objects.filter(user=user, problem_id__in=page_problem_ids)
            }
            bookmarked_id_set = set(
                user_profile.bookmarked_problems.filter(id__in=page_problem_ids).values_list('id', flat=True)
            ) if user_profile else set()
        else:
            user_progress_map = {}
            bookmarked_id_set = set()

        serializer_context = {
            'request': request,
            'user_progress_map': user_progress_map,
            'bookmarked_id_set': bookmarked_id_set,
        }
        serializer = ProblemListSerializer(page, many=True, context=serializer_context)
        response = paginator.get_paginated_response(serializer.data)
        response.data['counts'] = filter_counts
        return response


class ProblemDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get problem details",
        description="Detailed problem statement, constraints, examples, and judge configuration.",
        responses={200: ProblemSerializer},
    )
    def get(self, request, pk):
        try:
            problem = Problem.objects.prefetch_related('tags', 'companies').get(pk=pk)
        except Problem.DoesNotExist:
            return Response({'error': 'Problem not found'}, status=status.HTTP_404_NOT_FOUND)

        if not problem.is_judge_ready and problem.leetcode_id:
            from tracker.services.problem_hydration_service import hydrate_problem_contract
            try:
                problem, _, _ = hydrate_problem_contract(problem)
            except Exception:
                pass

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
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            problem = Problem.objects.get(pk=pk)
        except Problem.DoesNotExist:
            return Response({'available': False, 'message': 'Problem not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        def build_solution_data(sol):
            code_by_lang = dict(sol.code_by_language or {})
            if sol.language and sol.code and sol.language not in code_by_lang:
                code_by_lang[sol.language] = sol.code
            return {
                'available': True,
                'question_number': sol.question_number or problem.leetcode_id or problem.question_number,
                'title': sol.title,
                'description': sol.description or problem.description,
                'code': sol.code,
                'language': sol.language,
                'code_by_language': code_by_lang,
                'explanation': sol.explanation,
                'solution': sol.explanation,
                'time_complexity': sol.time_complexity,
                'space_complexity': sol.space_complexity,
                'source_url': sol.source_url,
                'solution_source_url': sol.solution_source_url,
            }

        cached = None
        try:
            cached = Solution.objects.get(problem=problem)
        except Solution.DoesNotExist:
            cached = None

        # Serve fresh successful cache directly — skip fetch entirely
        if cached and cached.is_fresh and not cached.fetch_failed and (cached.code or cached.code_by_language):
            return Response(build_solution_data(cached))

        if not problem.leetcode_id:
            if cached and not cached.fetch_failed and (cached.code or cached.code_by_language):
                return Response(build_solution_data(cached))
            return Response({'available': False, 'message': 'No LeetCode ID for this problem; solution unavailable.'},
                            status=status.HTTP_404_NOT_FOUND)

        # If a failed record exists but was attempted recently, don't hammer upstream again.
        # should_retry_failed is True only after 1 hour since the last failure.
        if cached and cached.fetch_failed and not getattr(cached, 'should_retry_failed', True):
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
                    'question_number': fetched.get('question_number') or problem.leetcode_id or problem.question_number,
                    'title': fetched.get('title') or problem.title,
                    'description': desc,
                    'code': fetched.get('code') or '# Solution not available',
                    'code_by_language': fetched.get('code_by_language') or {},
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
            return Response(build_solution_data(sol))

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

        queryset = queryset.distinct()

        random_mode = request.query_params.get('random') == 'true' or request.query_params.get('sort') == 'random'
        if random_mode:
            queryset = queryset.order_by('?')
        else:
            sort = request.query_params.get('sort')
            order_map = {
                'frequency': ('-frequency', 'question_number'),
                'created': ('-created_at', 'question_number'),
                'updated': ('-updated_at', 'question_number'),
                'title': ('title', 'question_number'),
                'frequency_asc': ('frequency', 'question_number'),
                'question_number': ('question_number',),
                '-question_number': ('-question_number',),
                'difficulty_asc': ('difficulty', 'question_number'),
                'difficulty_desc': ('-difficulty', 'question_number'),
            }
            order_fields = order_map.get(sort, ('-frequency', 'question_number'))
            queryset = queryset.order_by(*order_fields)

        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)

        # Batch preload user progress and bookmarks for this page to eliminate N+1 queries
        if user and page:
            page_problem_ids = [p.id for p in page]
            user_progress_map = {
                up.problem_id: up
                for up in UserProblemProgress.objects.filter(user=user, problem_id__in=page_problem_ids)
            }
            user_profile = getattr(user, 'profile', None) or UserProfile.objects.filter(user=user).first()
            bookmarked_id_set = set(
                user_profile.bookmarked_problems.filter(id__in=page_problem_ids).values_list('id', flat=True)
            ) if user_profile else set()
        else:
            user_progress_map = {}
            bookmarked_id_set = set()

        serializer_context = {
            'request': request,
            'user_progress_map': user_progress_map,
            'bookmarked_id_set': bookmarked_id_set,
        }
        serializer = ProblemListSerializer(page, many=True, context=serializer_context)
        response = paginator.get_paginated_response(serializer.data)
        response.data['company'] = CompanySerializer(company, context={'request': request}).data
        return response


class CompanyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        companies = Company.objects.annotate(problem_count=Count('problems'))
        if search:
            companies = companies.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        companies = companies.order_by('name')
        serializer = CompanySerializer(companies, many=True, context={'request': request})
        return Response(serializer.data)


class UserProgressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update problem practice progress",
        description="Records a review attempt and updates Leitner 5-box spaced repetition intervals.",
        responses={200: UserProblemProgressSerializer},
    )
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
        topic_map = {t['name']: t for t in topic_data.get('topics', [])}

        profile, _ = UserProfile.objects.get_or_create(user=user)
        custom_topics = profile.focus_topics.all()
        is_custom_focus = custom_topics.exists()

        if is_custom_focus:
            focus_topics_detail = []
            for tag in custom_topics:
                matched = topic_map.get(tag.name)
                if matched:
                    focus_topics_detail.append({
                        'id': tag.id,
                        'name': tag.name,
                        'slug': tag.slug,
                        'color': tag.color,
                        'solved': matched['solved'],
                        'total': matched['total'],
                        'percentage': matched['percentage'],
                        'is_custom': True,
                    })
                else:
                    tot = Problem.objects.filter(tags=tag).count()
                    sol = UserProblemProgress.objects.filter(user=user, problem__tags=tag, status='SOLVED').count()
                    pct = round((sol / tot * 100), 1) if tot > 0 else 0
                    focus_topics_detail.append({
                        'id': tag.id,
                        'name': tag.name,
                        'slug': tag.slug,
                        'color': tag.color,
                        'solved': sol,
                        'total': tot,
                        'percentage': pct,
                        'is_custom': True,
                    })
            weak_topics = [t['name'] for t in focus_topics_detail]
        else:
            focus_topics_detail = [
                {**t, 'is_custom': False}
                for t in topic_data.get('topics', []) if t.get('is_weak')
            ][:5]
            weak_topics = [t['name'] for t in focus_topics_detail]

        return Response({
            'total_problems': total_problems,
            'total_solved': total_solved,
            'total_attempted': total_attempted,
            'total_revisit': total_revisit,
            'current_streak': streak_data['current_streak'],
            'longest_streak': streak_data['longest_streak'],
            'due_today_count': box_stats['due_today_count'],
            'weak_topics': weak_topics,
            'focus_topics_detail': focus_topics_detail,
            'is_custom_focus': is_custom_focus,
        })


class UserFocusTopicsView(APIView):
    """
    Get or update custom focus topics for the authenticated user.
    GET: Returns list of user's focus topics (or auto-detected weak topics if none set).
    PUT: Sets custom focus topics (maximum 5). Pass empty list to reset to auto-detection.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_request_user(request)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        topic_data = get_user_topic_breakdown(user)
        topic_map = {t['slug']: t for t in topic_data.get('topics', [])}
        topic_map.update({str(t['id']): t for t in topic_data.get('topics', [])})
        topic_map.update({t['name']: t for t in topic_data.get('topics', [])})

        custom_topics = profile.focus_topics.all()
        is_custom = custom_topics.exists()

        if is_custom:
            results = []
            for tag in custom_topics:
                matched = topic_map.get(tag.slug) or topic_map.get(str(tag.id)) or topic_map.get(tag.name)
                if matched:
                    results.append({
                        'id': tag.id,
                        'name': tag.name,
                        'slug': tag.slug,
                        'color': tag.color,
                        'solved': matched['solved'],
                        'total': matched['total'],
                        'percentage': matched['percentage'],
                        'is_custom': True,
                    })
                else:
                    tot = Problem.objects.filter(tags=tag).count()
                    sol = UserProblemProgress.objects.filter(user=user, problem__tags=tag, status='SOLVED').count()
                    pct = round((sol / tot * 100), 1) if tot > 0 else 0
                    results.append({
                        'id': tag.id,
                        'name': tag.name,
                        'slug': tag.slug,
                        'color': tag.color,
                        'solved': sol,
                        'total': tot,
                        'percentage': pct,
                        'is_custom': True,
                    })
        else:
            results = [
                {**t, 'is_custom': False}
                for t in topic_data.get('topics', []) if t.get('is_weak')
            ][:5]

        return Response({
            'focus_topics': results,
            'is_custom': is_custom,
        })

    def put(self, request):
        user = get_request_user(request)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        topic_identifiers = request.data.get('topic_ids', [])

        if not isinstance(topic_identifiers, list):
            return Response({'error': 'topic_ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        if len(topic_identifiers) > 5:
            return Response({'error': 'Maximum 5 focus topics allowed'}, status=status.HTTP_400_BAD_REQUEST)

        if len(topic_identifiers) == 0:
            profile.focus_topics.clear()
            return self.get(request)

        q = Q()
        for ident in topic_identifiers:
            ident_str = str(ident).strip()
            if ident_str.isdigit():
                q |= Q(id=int(ident_str))
            else:
                q |= Q(slug__iexact=ident_str) | Q(name__iexact=ident_str)

        matched_tags = list(Tag.objects.filter(q))
        profile.focus_topics.set(matched_tags)
        return self.get(request)


class TopicPracticeView(APIView):
    """
    Returns prioritized practice problems for a specific topic.
    Prioritizes:
    1. Problems marked NEEDS_REVISIT or UNSOLVED
    2. Easy and Medium difficulties first
    3. High interview frequency
    """
    permission_classes = [AllowAny]

    def get(self, request):
        topic_param = request.query_params.get('topic', '').strip()
        if not topic_param:
            return Response({'error': 'Query parameter "topic" is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tag = Tag.objects.filter(Q(slug__iexact=topic_param) | Q(name__iexact=topic_param)).first()
        except Exception:
            tag = None

        if not tag:
            return Response({'error': f'Topic "{topic_param}" not found.'}, status=status.HTTP_404_NOT_FOUND)

        user = get_request_user(request)
        user_profile = getattr(user, 'profile', None) if user else None

        base_qs = Problem.objects.filter(tags=tag).prefetch_related('tags', 'companies')
        total_problems = base_qs.count()

        if user:
            solved_ids = set(
                UserProblemProgress.objects.filter(
                    user=user, problem__tags=tag, status='SOLVED'
                ).values_list('problem_id', flat=True)
            )
            revisit_ids = set(
                UserProblemProgress.objects.filter(
                    user=user, problem__tags=tag, status='NEEDS_REVISIT'
                ).values_list('problem_id', flat=True)
            )

            # Prioritize revisit first, then completely unsolved
            revisit_problems = list(base_qs.filter(id__in=revisit_ids).order_by('-frequency', 'difficulty')[:5])
            unsolved_problems = list(base_qs.exclude(id__in=solved_ids | revisit_ids).order_by('-frequency', 'difficulty')[:10])

            selected_problems = (revisit_problems + unsolved_problems)[:10]
            # Fallback if all are solved: just return top problems in topic
            if not selected_problems:
                selected_problems = list(base_qs.order_by('-frequency', 'difficulty')[:10])

            selected_ids = [p.id for p in selected_problems]
            user_progress_map = {
                up.problem_id: up
                for up in UserProblemProgress.objects.filter(user=user, problem_id__in=selected_ids)
            }
            bookmarked_id_set = set(
                user_profile.bookmarked_problems.filter(id__in=selected_ids).values_list('id', flat=True)
            ) if user_profile else set()
        else:
            selected_problems = list(base_qs.order_by('-frequency', 'difficulty')[:10])
            user_progress_map = {}
            bookmarked_id_set = set()

        serializer_context = {
            'request': request,
            'user_progress_map': user_progress_map,
            'bookmarked_id_set': bookmarked_id_set,
        }
        serialized_problems = ProblemListSerializer(selected_problems, many=True, context=serializer_context).data
        target_problem = serialized_problems[0] if serialized_problems else None

        return Response({
            'topic': {
                'id': tag.id,
                'name': tag.name,
                'slug': tag.slug,
                'color': tag.color,
                'total_problems': total_problems,
            },
            'target_problem': target_problem,
            'problems': serialized_problems,
        })


# Phase 2 Spaced Repetition Endpoints
class DueTodayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Problems due for review today",
        description="Returns problems in the Leitner spaced repetition system scheduled for review.",
        responses={200: ProblemListSerializer(many=True)},
    )
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

    @extend_schema(
        summary="Register user",
        description="Creates a new user account and dispatches an email verification link.",
        responses={201: OpenApiResponse(description="Account created successfully")},
    )
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
        if not sent:
            logger.warning("[EMAIL DEBUG] Verification email could not be sent on registration for user=%s (%s)", user.username, user.email)
        else:
            logger.info("[EMAIL DEBUG] Verification email sent successfully on registration for user=%s (%s)", user.username, user.email)

        return Response({
            'message': 'Account created. Please check your email to verify your account.' if sent else 'Account created, but verification email failed to send. Please use Resend Verification.',
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

    @extend_schema(
        summary="Log in user",
        description="Authenticates with username/email and password, returning JWT access and refresh tokens.",
        responses={200: OpenApiResponse(description="Login successful with tokens and user object")},
    )
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
        logger.info("[VERIFY DEBUG] verification endpoint reached")
        token = (request.data.get('token') or '').strip()
        has_token = bool(token)
        logger.info("[VERIFY DEBUG] token received: %s", str(has_token).lower())
        if not has_token:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("[VERIFY DEBUG] token length: %d", len(token))
        token_hash = hash_token(token)
        logger.info("[VERIFY DEBUG] token hash calculated")

        try:
            profile = UserProfile.objects.select_related('user').get(email_verification_token_hash=token_hash)
            logger.info("[VERIFY DEBUG] matching token record found: true")
            logger.info("[VERIFY DEBUG] user found: true")
        except UserProfile.DoesNotExist:
            logger.warning("[VERIFY DEBUG] matching token record found: false")
            logger.warning("[VERIFY DEBUG] user found: false")
            return Response({'error': 'Invalid or expired verification token.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already verified (preserve single-use semantics: cannot verify twice)
        if profile.is_email_verified:
            logger.info("[VERIFY DEBUG] token already used: true")
            return Response({
                'error': 'This verification token has already been used. Please log in.',
                'code': 'already_used',
                'user': {
                    'id': profile.user.id,
                    'username': profile.user.username,
                    'email': profile.user.email,
                    'is_email_verified': True,
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info("[VERIFY DEBUG] token already used: false")
        expired = is_token_expired(profile.email_verification_sent_at, getattr(settings, 'EMAIL_VERIFICATION_EXPIRY_HOURS', 24))
        logger.info("[VERIFY DEBUG] token expired: %s", str(expired).lower())
        if expired:
            return Response({'error': 'Verification link expired. Please request a new one.', 'code': 'expired'},
                            status=status.HTTP_400_BAD_REQUEST)

        profile.is_email_verified = True
        # Do not immediately clear email_verification_token_hash so subsequent requests can detect 'already_used'
        profile.save(update_fields=['is_email_verified'])
        logger.info("[VERIFY DEBUG] verification successful")

        return Response({
            'message': 'Email verified successfully. You can now log in.',
            'user': {
                'id': profile.user.id,
                'username': profile.user.username,
                'email': profile.user.email,
                'is_email_verified': True,
            }
        }, status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    """Resend email verification for an unverified account.

    POST /api/auth/resend-verification/
    Body: { "email": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        logger.info("[EMAIL DEBUG] resend endpoint reached for email=%s", email)
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Always succeed to avoid email enumeration
            logger.info("[EMAIL DEBUG] resend requested for non-existent email=%s; pretending success", email)
            return Response({'message': 'If an account with that email exists, a verification email has been sent.'})

        profile = get_or_create_profile(user)
        if profile.is_email_verified:
            logger.info("[EMAIL DEBUG] resend requested for already verified email=%s", email)
            return Response({'message': 'Email already verified. Please log in.'})

        token = generate_auth_token()
        profile.email_verification_token_hash = hash_token(token)
        profile.email_verification_sent_at = timezone.now()
        profile.save()
        sent = send_verification_email(user, token)
        if not sent:
            logger.error("[EMAIL DEBUG] send_verification_email failed for email=%s", email)
            return Response(
                {
                    'error': 'Failed to send verification email. Please check email service configuration.',
                    'verification_email_sent': False,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        logger.info("[EMAIL DEBUG] send_verification_email succeeded for email=%s", email)
        return Response({'message': 'Verification email sent.', 'verification_email_sent': True})


class ForgotPasswordView(APIView):
    """Request a password reset email.

    POST /api/auth/forgot-password/
    Body: { "email": "string" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        logger.info("[EMAIL DEBUG] forgot-password endpoint reached for email=%s", email)
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Always succeed to avoid email enumeration
        message = {'message': 'If an account with that email exists, a password reset link has been sent.'}

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            logger.info("[EMAIL DEBUG] forgot-password requested for non-existent email=%s; pretending success", email)
            return Response(message)

        profile = get_or_create_profile(user)
        token = generate_auth_token()
        profile.password_reset_token_hash = hash_token(token)
        profile.password_reset_sent_at = timezone.now()
        profile.save()

        sent = send_password_reset_email(user, token)
        if not sent:
            logger.error("[EMAIL DEBUG] send_password_reset_email failed for email=%s", email)
        else:
            logger.info("[EMAIL DEBUG] send_password_reset_email succeeded for email=%s", email)
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


class LogoutView(APIView):
    """
    Revoke a refresh token on user logout.

    POST /api/auth/logout/
    Body: { "refresh_token": "string" }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Log out user",
        description="Revokes the provided refresh token so it cannot be used again.",
        responses={200: OpenApiResponse(description="Logged out successfully")},
    )
    def post(self, request):
        refresh_token = (request.data.get('refresh_token') or '').strip()
        if not refresh_token:
            return Response({'error': 'refresh_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hash_token(refresh_token)
        token_record = RefreshToken.objects.filter(token_hash=token_hash).first()
        if token_record:
            token_record.revoked = True
            token_record.revoked_at = timezone.now()
            token_record.save(update_fields=['revoked', 'revoked_at'])

        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """Refresh an access token using a valid refresh token.

    POST /api/auth/refresh-token/
    Body: { "refresh_token": "string" }
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh access token",
        description="Verifies the refresh token, revokes it (token rotation), and issues a new pair of access + refresh tokens.",
        responses={200: OpenApiResponse(description="New access and refresh token pair")},
    )
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

        token_hash = hash_token(refresh_token)
        token_record = RefreshToken.objects.filter(token_hash=token_hash).first()
        if not token_record:
            return Response({'error': 'Invalid or unknown refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)

        if token_record.revoked:
            return Response({'error': 'Refresh token has been revoked.'}, status=status.HTTP_401_UNAUTHORIZED)

        if token_record.expires_at <= timezone.now():
            return Response({'error': 'Refresh token has expired.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(pk=payload.get('user_id'))
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)

        # Revoke the old refresh token upon rotation
        token_record.revoked = True
        token_record.revoked_at = timezone.now()
        token_record.save(update_fields=['revoked', 'revoked_at'])

        # Issue new tokens (which creates a new RefreshToken record)
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

    @extend_schema(
        summary="User analytics dashboard",
        description="Returns placement readiness score, streak history, topic mastery, and recent activity.",
        responses={200: OpenApiResponse(description="Aggregated user dashboard analytics")},
    )
    def get(self, request):
        dashboard = get_user_dashboard(request.user)
        return Response(dashboard)


# ============================================================================
# V2 VIEWS — Online Judge
# ============================================================================

class RunCodeView(APIView):
    """
    POST /api/run-code/
    Execute code with custom stdin. Does NOT alter any progress or save a Submission.
    Body: { language, source_code, stdin, problem_id (optional) }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [JudgeRunThrottle]

    @extend_schema(
        summary="Run code in sandbox",
        description="Executes user-provided code against custom stdin without recording a submission.",
        responses={200: OpenApiResponse(description="Execution result with output and performance metrics")},
    )
    def post(self, request):
        from tracker.services.judge_service import run_code_for_user

        # Load check: if system has too many pending judge submissions, return 503
        pending_count = Submission.objects.filter(verdict='PENDING').count()
        if pending_count > 30:
            return Response(
                {'error': 'System is experiencing high judge load. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        language = request.data.get('language', '').strip().lower()
        source_code = request.data.get('source_code', '')
        stdin = request.data.get('stdin', '')
        problem_id = request.data.get('problem_id', '')

        if not language:
            return Response({'error': 'language is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not source_code.strip():
            return Response({'error': 'source_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        result = run_code_for_user(request.user, problem_id, language, source_code, stdin)
        return Response(result)


class SubmitCodeView(APIView):
    """
    POST /api/submit/
    Submit code asynchronously for judging against all test cases (visible + hidden).
    Body: { language, source_code, problem_id }
    Returns 202 Accepted: { "submission_id": ..., "status": "PENDING", "verdict": "PENDING" }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [JudgeSubmitThrottle]

    @extend_schema(
        summary="Submit solution for judging",
        description="Creates a pending submission and dispatches evaluation to background Celery queue. Returns 202 Accepted.",
        responses={202: OpenApiResponse(description="Pending submission created")},
    )
    def post(self, request):
        from tracker.services.judge_service import create_pending_submission
        from tracker.tasks import run_submission_task

        language = request.data.get('language', '').strip().lower()
        source_code = request.data.get('source_code', '')
        problem_id = request.data.get('problem_id', '')

        if not language:
            return Response({'error': 'language is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not source_code.strip():
            return Response({'error': 'source_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not problem_id:
            return Response({'error': 'problem_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for same-problem pending submission cooldown (prevents spamming queue)
        pending_sub = Submission.objects.filter(
            user=request.user, problem_id=problem_id, verdict='PENDING'
        ).first()
        if pending_sub:
            return Response({
                'error': 'You already have a pending submission for this problem. Please wait for it to complete.',
                'submission_id': str(pending_sub.id),
                'status': 'PENDING',
                'verdict': 'PENDING',
            }, status=status.HTTP_409_CONFLICT)

        try:
            submission = create_pending_submission(request.user, problem_id, language, source_code)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Problem.DoesNotExist:
            return Response({'error': 'Problem not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Dispatch async Celery task
        run_submission_task.delay(str(submission.id))

        return Response({
            'submission_id': str(submission.id),
            'status': 'PENDING',
            'verdict': 'PENDING',
            'tests_passed': 0,
            'tests_total': 0,
        }, status=status.HTTP_202_ACCEPTED)


class SubmissionStatusView(APIView):
    """
    GET /api/submissions/<uuid:pk>/status/
    Lightweight endpoint for polling submission evaluation status.
    Returns: { "submission_id": ..., "verdict": ..., "tests_passed": ..., "tests_total": ... }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Check submission evaluation status",
        description="Lightweight polling endpoint to retrieve current evaluation state and test metrics.",
        responses={200: OpenApiResponse(description="Submission evaluation verdict and progress")},
    )
    def get(self, request, pk):
        try:
            s = Submission.objects.get(id=pk, user=request.user)
        except (Submission.DoesNotExist, ValueError):
            return Response({'error': 'Submission not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'submission_id': str(s.id),
            'verdict': s.verdict,
            'tests_passed': s.tests_passed,
            'tests_total': s.tests_total,
        })


class ProblemSubmissionsView(APIView):
    """GET /api/problems/<uuid>/submissions/ — user's own submissions for a problem."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List user problem submissions",
        description="Returns submission history for a specific problem for the authenticated user.",
        responses={200: SubmissionSerializer(many=True)},
    )
    def get(self, request, pk):
        from tracker.services.judge_service import get_submission_history
        history = get_submission_history(request.user, str(pk))
        return Response({'submissions': history})


class SubmissionDetailView(APIView):
    """GET /api/submissions/<uuid>/ — full detail for a single submission (own only)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get submission details",
        description="Returns full diagnostic and per-test execution details for a submission.",
        responses={200: SubmissionDetailSerializer},
    )
    def get(self, request, pk):
        from tracker.services.judge_service import get_submission_detail
        detail = get_submission_detail(request.user, str(pk))
        if detail is None:
            return Response({'error': 'Submission not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(detail)


class LanguagesView(APIView):
    """GET /api/languages/ — list supported languages and default starter code."""
    permission_classes = [AllowAny]

    def get(self, request):
        from tracker.services.judge_service import get_supported_languages
        return Response({'languages': get_supported_languages()})


class LanguageTemplateView(APIView):
    """GET /api/problems/<uuid>/language-template/?language=python — starter code."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        from tracker.services.judge_service import get_language_template
        from tracker.services.problem_hydration_service import hydrate_problem_contract
        try:
            problem = Problem.objects.get(pk=pk)
            if not problem.is_judge_ready and problem.leetcode_id:
                hydrate_problem_contract(problem)
        except Exception:
            pass
        language = request.query_params.get('language', 'python').strip().lower()
        starter = get_language_template(str(pk), language)
        return Response({'language': language, 'starter_code': starter})


class ProblemTestCasesView(APIView):
    """GET /api/problems/<uuid>/test-cases/ — VISIBLE test cases only (never hidden)."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        from tracker.services.problem_hydration_service import hydrate_problem_contract
        try:
            problem = Problem.objects.get(pk=pk)
            if not problem.is_judge_ready and problem.leetcode_id:
                hydrate_problem_contract(problem)
        except Exception:
            pass
        test_cases = TestCase.objects.filter(problem_id=pk, is_hidden=False).order_by('order')
        serializer = TestCaseSerializer(test_cases, many=True)
        return Response({'test_cases': serializer.data})


# ============================================================================
# V2 VIEWS — Challenges
# ============================================================================

class ChallengeListView(APIView):
    """
    GET  /api/challenges/ — list active challenges + history
    POST /api/challenges/ — create a new challenge
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tracker.services.challenge_service import get_active_challenges, get_challenge_history
        active = get_active_challenges(request.user)
        history = get_challenge_history(request.user)
        return Response({'active': active, 'history': history})

    def post(self, request):
        from tracker.services.challenge_service import create_challenge
        try:
            if not request.data.get('title'):
                return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)
            challenge = create_challenge(request.user, request.data)
            serializer = ChallengeSerializer(challenge)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChallengeDetailView(APIView):
    """GET/DELETE /api/challenges/<uuid>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from tracker.services.challenge_service import check_challenge_progress
        try:
            challenge = Challenge.objects.get(id=pk, user=request.user)
        except Challenge.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        progress = check_challenge_progress(request.user, str(pk))
        serializer = ChallengeSerializer(challenge)
        return Response({**serializer.data, **progress})

    def delete(self, request, pk):
        try:
            challenge = Challenge.objects.get(id=pk, user=request.user, status='ACTIVE')
            challenge.status = 'CANCELLED'
            challenge.save()
            return Response({'status': 'cancelled'})
        except Challenge.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class ChallengeCompleteView(APIView):
    """POST /api/challenges/<uuid>/complete/ — manually finalize a challenge."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from tracker.services.challenge_service import finalize_challenge
        try:
            challenge = Challenge.objects.get(id=pk, user=request.user, status='ACTIVE')
        except Challenge.DoesNotExist:
            return Response({'error': 'Active challenge not found.'}, status=status.HTTP_404_NOT_FOUND)
        result = finalize_challenge(challenge, request.user)
        return Response(result)


# ============================================================================
# V2 VIEWS — Points & Achievements
# ============================================================================

class UserPointsView(APIView):
    """GET /api/points/ — current point totals (read-only)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tracker.services.points_service import get_user_points
        return Response(get_user_points(request.user))


class AchievementListView(APIView):
    """GET /api/achievements/ — all achievements with unlock status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tracker.services.achievement_service import get_user_achievements, seed_achievements
        seed_achievements()  # idempotent — ensure definitions exist
        achievements = get_user_achievements(request.user)
        return Response({'achievements': achievements})


# ============================================================================
# V2 VIEWS — Notifications
# ============================================================================

class NotificationListView(APIView):
    """GET /api/notifications/ — recent notifications for current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tracker.services.notification_service import get_notifications, get_unread_count
        unread_only = request.query_params.get('unread') == 'true'
        notifications = get_notifications(request.user, unread_only=unread_only)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'notifications': serializer.data,
            'unread_count': get_unread_count(request.user),
        })


class NotificationReadView(APIView):
    """POST /api/notifications/<uuid>/read/ — mark a notification as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from tracker.services.notification_service import mark_read
        updated = mark_read(request.user, pk)
        if not updated:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'read'})


class NotificationReadAllView(APIView):
    """POST /api/notifications/read-all/ — mark all notifications as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from tracker.services.notification_service import mark_all_read
        count = mark_all_read(request.user)
        return Response({'marked_read': count})


# ============================================================================
# V2 VIEWS — Interview Simulation
# ============================================================================

class InterviewSessionListView(APIView):
    """
    GET  /api/interview-sessions/ — list past sessions
    POST /api/interview-sessions/ — start a new session
    Body: { duration_minutes, num_problems, difficulty, company_id (optional) }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = InterviewSession.objects.filter(user=request.user)[:20]
        serializer = InterviewSessionSerializer(sessions, many=True)
        return Response({'sessions': serializer.data})

    def post(self, request):
        duration = int(request.data.get('duration_minutes', 45))
        num_problems = int(request.data.get('num_problems', 2))
        difficulty = request.data.get('difficulty', 'Medium')
        company_id = request.data.get('company_id')

        # Select random problems based on difficulty
        problems_qs = Problem.objects.all()
        if difficulty != 'Mixed':
            problems_qs = problems_qs.filter(difficulty=difficulty)
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                problems_qs = problems_qs.filter(companies=company)
            except Company.DoesNotExist:
                company = None
        else:
            company = None

        # Avoid already-solved problems first, then fall back
        user_solved_ids = UserProblemProgress.objects.filter(
            user=request.user, status='SOLVED'
        ).values_list('problem_id', flat=True)
        unsolved = problems_qs.exclude(id__in=user_solved_ids).order_by('?')[:num_problems]
        selected = list(unsolved)
        if len(selected) < num_problems:
            remaining = num_problems - len(selected)
            fallback = problems_qs.exclude(
                id__in=[p.id for p in selected]
            ).order_by('?')[:remaining]
            selected.extend(fallback)

        if not selected:
            return Response(
                {'error': 'No problems available for these criteria.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = InterviewSession.objects.create(
            user=request.user,
            duration_minutes=duration,
            num_problems=num_problems,
            difficulty=difficulty,
            company=company,
            status='ACTIVE',
        )
        for prob in selected:
            InterviewProblem.objects.create(session=session, problem=prob)

        serializer = InterviewSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InterviewSessionDetailView(APIView):
    """GET /api/interview-sessions/<uuid>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = InterviewSession.objects.get(id=pk, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = InterviewSessionSerializer(session)
        return Response(serializer.data)


class InterviewSessionEndView(APIView):
    """POST /api/interview-sessions/<uuid>/end/ — end a session and compute score."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from tracker.services.points_service import award_points
        from tracker.services.achievement_service import check_and_unlock_achievements
        from tracker.models import ActivityEvent
        from tracker.scoring import POINTS_INTERVIEW_PROBLEM_SOLVED, POINTS_INTERVIEW_PERFECT

        try:
            session = InterviewSession.objects.get(id=pk, user=request.user, status='ACTIVE')
        except InterviewSession.DoesNotExist:
            return Response({'error': 'Active session not found.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        session.ended_at = now
        session.status = 'COMPLETED'

        # Tally solved problems
        solved = InterviewProblem.objects.filter(session=session, solved=True).count()
        session.problems_solved = solved

        # Score: points per solved problem
        score = solved * POINTS_INTERVIEW_PROBLEM_SOLVED
        if solved == session.num_problems:
            score += POINTS_INTERVIEW_PERFECT
        session.score = score
        session.save()

        if score > 0:
            award_points(
                request.user,
                reason='interview_simulation',
                amount=score,
                metadata={'session_id': str(session.id), 'solved': solved},
            )

        # Check achievements
        check_and_unlock_achievements(request.user)

        ActivityEvent.objects.create(
            user=request.user,
            event_type='INTERVIEW_COMPLETED',
            metadata={
                'session_id': str(session.id),
                'score': score,
                'solved': solved,
                'total': session.num_problems,
            },
        )

        serializer = InterviewSessionSerializer(session)
        return Response({
            **serializer.data,
            'score': score,
            'follow_up_actions': _get_interview_follow_up(request.user, session),
        })


def _get_interview_follow_up(user, session) -> list[str]:
    """Deterministic rule-based follow-up recommendations after interview simulation."""
    actions = []
    from tracker.services.leitner import get_leitner_box_stats
    stats = get_leitner_box_stats(user)

    if stats['due_today_count'] > 0:
        actions.append(f'Complete {stats["due_today_count"]} due Leitner review(s)')

    unsolved = InterviewProblem.objects.filter(session=session, solved=False).select_related('problem')
    for ip in unsolved:
        actions.append(f'Review failed problem: {ip.problem.title} ({ip.problem.difficulty})')

    if not actions:
        actions.append('Practice 2 more Medium problems')

    return actions[:5]


class InterviewProblemSolveView(APIView):
    """
    POST /api/interview-sessions/<session_uuid>/problems/<problem_uuid>/solve/
    Mark a problem as solved within a session (called after Accepted submission).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_pk, problem_pk):
        try:
            session = InterviewSession.objects.get(id=session_pk, user=request.user, status='ACTIVE')
            ip = InterviewProblem.objects.get(session=session, problem_id=problem_pk)
        except (InterviewSession.DoesNotExist, InterviewProblem.DoesNotExist):
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        ip.solved = True
        ip.attempts += 1
        ip.save()
        return Response({'solved': True})


# ============================================================================
# V2 VIEWS — DSA Patterns & Enhanced Analytics
# ============================================================================

class PatternListView(APIView):
    """GET /api/patterns/ — all DSA patterns."""
    permission_classes = [AllowAny]

    def get(self, request):
        patterns = DSAPattern.objects.all()
        serializer = DSAPatternSerializer(patterns, many=True)
        return Response({'patterns': serializer.data})


class TopicMasteryView(APIView):
    """GET /api/analytics/mastery/ — topic mastery with 5-level labels."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mastery = get_topic_mastery_levels(request.user)
        return Response(mastery)


class RevisionQueueView(APIView):
    """GET /api/analytics/revision-queue/ — deterministic revision queue."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queue = get_revision_queue(request.user)
        return Response({'revision_queue': queue, 'count': len(queue)})


class CompanyTrackView(APIView):
    """GET /api/analytics/company-track/<company_slug>/ — company preparation track."""
    permission_classes = [IsAuthenticated]

    def get(self, request, company_slug):
        track = get_company_track(request.user, company_slug)
        if not track:
            return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(track)
