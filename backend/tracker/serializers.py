from rest_framework import serializers
from tracker.models import (
    Tag, Company, Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay, UserProfile, Solution,
    Submission, Challenge, ChallengeProblem, Achievement, UserAchievement,
    Notification, InterviewSession, InterviewProblem, DSAPattern, TestCase,
    UserPoints,
)
from tracker.utils.problem_formatter import clean_broken_newlines, parse_structured_statement

def get_serializer_user(request):
    if not request:
        return None
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return request.user
    return None

class TagSerializer(serializers.ModelSerializer):
    problem_count = serializers.IntegerField(read_only=True, default=0)
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color', 'category', 'problem_count', 'user_progress']

    def get_user_progress(self, obj):
        request = self.context.get('request')
        user = get_serializer_user(request)
        result = {'solved': 0}
        if user:
            solved = UserProblemProgress.objects.filter(
                user=user, problem__tags=obj, status='SOLVED'
            ).count()
            result['solved'] = solved
        return result

class CompanySerializer(serializers.ModelSerializer):
    problem_count = serializers.IntegerField(read_only=True, default=0)
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'slug', 'problem_count', 'user_progress']

    def get_user_progress(self, obj):
        request = self.context.get('request')
        user = get_serializer_user(request)
        result = {'solved': 0}
        if user:
            solved = UserProblemProgress.objects.filter(
                user=user, problem__companies=obj, status='SOLVED'
            ).count()
            result['solved'] = solved
        return result

class UserProblemProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProblemProgress
        fields = [
            'id', 'problem', 'status', 'times_solved', 'times_attempted',
            'last_attempted', 'last_solved', 'notes', 'code_solution',
            'code_language', 'current_box', 'next_review_date', 'reviews_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class TagSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color', 'category']

class CompanySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'slug']

class ProblemSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    companies = CompanySerializer(many=True, read_only=True)
    user_progress = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    leetcode_url = serializers.SerializerMethodField()
    solution_api_url = serializers.SerializerMethodField()
    has_solution = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'question_number', 'title', 'slug', 'difficulty', 'description',
            'execution_mode', 'input_format', 'output_format',
            'function_name', 'class_name', 'parameters_meta', 'return_type',
            'is_judge_ready', 'judge_readiness_status', 'output_checker', 'missing_configuration',
            'examples', 'constraints',
            'tags', 'companies', 'source_url', 'source_platform',
            'time_limit_minutes', 'time_limit_ms', 'memory_limit_mb', 'leetcode_id', 'is_premium', 'frequency',
            'leetcode_url', 'solution_api_url', 'has_solution',
            'created_at', 'updated_at', 'user_progress', 'is_bookmarked'
        ]

    def get_user_progress(self, obj):
        user_progress_map = self.context.get('user_progress_map')
        if user_progress_map is not None:
            progress = user_progress_map.get(obj.id)
            return UserProblemProgressSerializer(progress).data if progress else None
        request = self.context.get('request')
        user = get_serializer_user(request)
        if user:
            progress = UserProblemProgress.objects.filter(user=user, problem=obj).first()
            if progress:
                return UserProblemProgressSerializer(progress).data
        return None

    def get_is_bookmarked(self, obj):
        bookmarked_id_set = self.context.get('bookmarked_id_set')
        if bookmarked_id_set is not None:
            return obj.id in bookmarked_id_set
        request = self.context.get('request')
        user = get_serializer_user(request)
        if user:
            return obj.bookmarked_by.filter(pk=user.pk).exists()
        return False

    def get_leetcode_url(self, obj):
        """Always link directly to LeetCode problem page (never leetcode.ca)."""
        if obj.leetcode_id:
            return f'https://leetcode.com/problems/{obj.slug}/'
        if obj.source_url:
            return obj.source_url
        return None

    def get_solution_api_url(self, obj):
        """Internal API endpoint for cached solution from leetcode.ca."""
        if obj.leetcode_id:
            return f'/api/problems/{obj.id}/solution/'
        return None

    def get_has_solution(self, obj):
        if hasattr(obj, 'cached_solution') and obj.cached_solution is not None:
            return not obj.cached_solution.fetch_failed
        return Solution.objects.filter(problem=obj, fetch_failed=False).exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        raw_desc = instance.description or ''
        data['clean_description'] = clean_broken_newlines(raw_desc)
        if not data.get('examples') or not data.get('constraints'):
            parsed = parse_structured_statement(raw_desc)
            if not data.get('examples') and parsed.get('examples'):
                data['examples'] = parsed['examples']
            if not data.get('constraints') and parsed.get('constraints'):
                data['constraints'] = parsed['constraints']
            if parsed.get('description'):
                data['clean_description'] = parsed['description']
        return data


class ProblemListSerializer(serializers.ModelSerializer):
    """
    Lightweight, high-performance serializer for problem lists and tables.
    Omits the large HTML/markdown problem description and uses lightweight
    Tag/Company serializers with zero N+1 nested queries.
    """
    tags = TagSimpleSerializer(many=True, read_only=True)
    companies = CompanySimpleSerializer(many=True, read_only=True)
    user_progress = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    leetcode_url = serializers.SerializerMethodField()
    solution_api_url = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'question_number', 'title', 'slug', 'difficulty',
            'is_judge_ready', 'judge_readiness_status',
            'tags', 'companies', 'source_url', 'source_platform',
            'time_limit_minutes', 'time_limit_ms', 'memory_limit_mb', 'leetcode_id', 'is_premium', 'frequency',
            'leetcode_url', 'solution_api_url',
            'created_at', 'updated_at', 'user_progress', 'is_bookmarked'
        ]

    def get_user_progress(self, obj):
        user_progress_map = self.context.get('user_progress_map')
        if user_progress_map is not None:
            progress = user_progress_map.get(obj.id)
            return UserProblemProgressSerializer(progress).data if progress else None
        request = self.context.get('request')
        user = get_serializer_user(request)
        if user:
            progress = UserProblemProgress.objects.filter(user=user, problem=obj).first()
            if progress:
                return UserProblemProgressSerializer(progress).data
        return None

    def get_is_bookmarked(self, obj):
        bookmarked_id_set = self.context.get('bookmarked_id_set')
        if bookmarked_id_set is not None:
            return obj.id in bookmarked_id_set
        request = self.context.get('request')
        user = get_serializer_user(request)
        if user:
            return obj.bookmarked_by.filter(pk=user.pk).exists()
        return False

    def get_leetcode_url(self, obj):
        if obj.leetcode_id:
            return f'https://leetcode.com/problems/{obj.slug}/'
        if obj.source_url:
            return obj.source_url
        return None

    def get_solution_api_url(self, obj):
        if obj.leetcode_id:
            return f'/api/problems/{obj.id}/solution/'
        return None

class ReviewHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHistory
        fields = ['id', 'old_box', 'new_box', 'action', 'notes', 'created_at']

class DailyStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStat
        fields = ['date', 'problems_solved', 'problems_attempted', 'total_time_minutes', 'by_topic']

class UserStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStreak
        fields = ['current_streak', 'longest_streak', 'last_solved_date']

class StudyPlanDaySerializer(serializers.ModelSerializer):
    problems = ProblemSerializer(many=True, read_only=True)

    class Meta:
        model = StudyPlanDay
        fields = ['id', 'date', 'problems', 'focus_topic', 'difficulty_target', 'reason']

class StudyPlanSerializer(serializers.ModelSerializer):
    days = StudyPlanDaySerializer(many=True, read_only=True)

    class Meta:
        model = StudyPlan
        fields = ['id', 'target_date', 'problems_per_day', 'is_active', 'created_at', 'days']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['is_email_verified']


class BookmarkedProblemSerializer(ProblemSerializer):
    """Subset of ProblemSerializer; in a bookmarks context the problem is always bookmarked."""

    def get_is_bookmarked(self, obj):
        return True


class SolutionSerializer(serializers.ModelSerializer):
    """Serializer for cached leetcode.ca solutions."""

    class Meta:
        model = Solution
        fields = [
            'id', 'question_number', 'title', 'description', 'code', 'language',
            'code_by_language', 'explanation',
            'time_complexity', 'space_complexity', 'source_url', 'solution_source_url',
            'last_fetched_at', 'fetch_failed', 'fetch_error'
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        cbl = dict(data.get('code_by_language') or {})
        lang = data.get('language') or 'python'
        code = data.get('code') or ''
        if lang and code and lang not in cbl:
            cbl[lang] = code
        data['code_by_language'] = cbl
        return data


# ============================================================================
# V2 Serializers
# ============================================================================

class SubmissionSerializer(serializers.ModelSerializer):
    """Safe submission serializer — never exposes hidden test I/O."""
    problem_title = serializers.SerializerMethodField()
    question_number = serializers.IntegerField(source='problem.question_number', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'problem', 'question_number', 'problem_title', 'language', 'verdict',
            'tests_passed', 'tests_total', 'execution_time_ms', 'memory_kb',
            'created_at',
        ]
        read_only_fields = fields

    def get_problem_title(self, obj):
        return obj.problem.title


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """Full submission detail for the submission owner."""
    problem_title = serializers.SerializerMethodField()
    question_number = serializers.IntegerField(source='problem.question_number', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'problem', 'question_number', 'problem_title', 'language', 'source_code',
            'verdict', 'tests_passed', 'tests_total', 'execution_time_ms',
            'memory_kb', 'compile_error', 'error_message', 'created_at',
        ]
        read_only_fields = fields

    def get_problem_title(self, obj):
        return obj.problem.title


class ChallengeProblemSerializer(serializers.ModelSerializer):
    problem_title = serializers.SerializerMethodField()
    problem_difficulty = serializers.SerializerMethodField()
    question_number = serializers.IntegerField(source='problem.question_number', read_only=True)

    class Meta:
        model = ChallengeProblem
        fields = ['id', 'problem', 'question_number', 'problem_title', 'problem_difficulty', 'completed', 'completed_at']

    def get_problem_title(self, obj):
        return obj.problem.title

    def get_problem_difficulty(self, obj):
        return obj.problem.difficulty


class ChallengeSerializer(serializers.ModelSerializer):
    challenge_problems = ChallengeProblemSerializer(many=True, read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'template', 'start_time', 'end_time',
            'target_count', 'points', 'bonus_points', 'status',
            'completed_count', 'points_earned', 'completed_at',
            'time_remaining_seconds', 'challenge_problems', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'completed_count', 'points_earned', 'completed_at', 'created_at']

    def get_time_remaining_seconds(self, obj):
        return obj.time_remaining_seconds


class AchievementSerializer(serializers.ModelSerializer):
    unlocked = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = [
            'id', 'code', 'name', 'description', 'icon', 'points',
            'sort_order', 'unlocked', 'unlocked_at',
        ]

    def get_unlocked(self, obj):
        request = self.context.get('request')
        user = get_serializer_user(request)
        if not user:
            return False
        return UserAchievement.objects.filter(user=user, achievement=obj).exists()

    def get_unlocked_at(self, obj):
        request = self.context.get('request')
        user = get_serializer_user(request)
        if not user:
            return None
        ua = UserAchievement.objects.filter(user=user, achievement=obj).first()
        return ua.unlocked_at if ua else None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'body', 'is_read', 'action_url', 'created_at']
        read_only_fields = fields


class InterviewProblemSerializer(serializers.ModelSerializer):
    problem_title = serializers.SerializerMethodField()
    problem_difficulty = serializers.SerializerMethodField()
    question_number = serializers.IntegerField(source='problem.question_number', read_only=True)
    solved = serializers.SerializerMethodField()

    class Meta:
        model = InterviewProblem
        fields = ['id', 'problem', 'question_number', 'problem_title', 'problem_difficulty', 'solved', 'attempts']

    def get_problem_title(self, obj):
        return obj.problem.title

    def get_problem_difficulty(self, obj):
        return obj.problem.difficulty

    def get_solved(self, obj):
        if obj.solved:
            return True
        if hasattr(obj, 'session') and obj.session:
            from tracker.models import Submission
            qs = Submission.objects.filter(
                user=obj.session.user,
                problem=obj.problem,
                verdict='ACCEPTED',
                created_at__gte=obj.session.started_at,
            )
            if obj.session.ended_at:
                qs = qs.filter(created_at__lte=obj.session.ended_at)
            accepted_sub = qs.order_by('-created_at').first()
            if accepted_sub:
                obj.solved = True
                obj.submission = accepted_sub
                if obj.attempts == 0:
                    obj.attempts = 1
                obj.save(update_fields=['solved', 'submission', 'attempts'])
                return True
        return False


class InterviewSessionSerializer(serializers.ModelSerializer):
    interview_problems = InterviewProblemSerializer(many=True, read_only=True)
    elapsed_minutes = serializers.SerializerMethodField()
    deadline = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSession
        fields = [
            'id', 'duration_minutes', 'num_problems', 'difficulty',
            'company', 'company_name', 'status', 'started_at', 'ended_at',
            'score', 'problems_solved', 'elapsed_minutes', 'deadline',
            'interview_problems',
        ]
        read_only_fields = ['id', 'started_at', 'ended_at', 'score', 'problems_solved', 'status']

    def get_elapsed_minutes(self, obj):
        return obj.elapsed_minutes

    def get_deadline(self, obj):
        return obj.deadline.isoformat()

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None


class DSAPatternSerializer(serializers.ModelSerializer):
    problem_count = serializers.SerializerMethodField()

    class Meta:
        model = DSAPattern
        fields = ['id', 'name', 'slug', 'description', 'problem_count']

    def get_problem_count(self, obj):
        return obj.problems.count()


class TestCaseSerializer(serializers.ModelSerializer):
    """Safe serializer — only for VISIBLE test cases (no hidden test I/O)."""
    class Meta:
        model = TestCase
        fields = ['id', 'input_text', 'expected_output', 'order']


class UserPointsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPoints
        fields = ['total', 'weekly', 'challenge_points', 'streak_points', 'updated_at']
        read_only_fields = fields
