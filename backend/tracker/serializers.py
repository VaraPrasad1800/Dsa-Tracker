from rest_framework import serializers
from tracker.models import (
    Tag, Company, Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay, UserProfile, Solution
)

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

class ProblemSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    companies = CompanySerializer(many=True, read_only=True)
    user_progress = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    leetcode_url = serializers.SerializerMethodField()
    solution_api_url = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'title', 'slug', 'difficulty', 'description',
            'tags', 'companies', 'source_url', 'source_platform',
            'time_limit_minutes', 'leetcode_id', 'is_premium', 'frequency',
            'leetcode_url', 'solution_api_url',
            'created_at', 'updated_at', 'user_progress', 'is_bookmarked'
        ]

    def get_user_progress(self, obj):
        request = self.context.get('request')
        user = get_serializer_user(request)
        if user:
            progress = UserProblemProgress.objects.filter(user=user, problem=obj).first()
            if progress:
                return UserProblemProgressSerializer(progress).data
        return None

    def get_is_bookmarked(self, obj):
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
            # This is the internal API route — frontend navigates to /problems/{id}/solution
            # and fetches from this endpoint
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
            'id', 'question_number', 'title', 'description', 'code', 'language', 'explanation',
            'time_complexity', 'space_complexity', 'source_url', 'solution_source_url',
            'last_fetched_at', 'fetch_failed', 'fetch_error'
        ]
        read_only_fields = fields
