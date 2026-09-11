from django.contrib import admin
from django.contrib.auth import get_user_model
from tracker.models import (
    Tag, Company, Problem, UserProblemProgress, ReviewHistory,
    DailyStat, UserStreak, StudyPlan, StudyPlanDay
)

User = get_user_model()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'problem_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    def problem_count(self, obj):
        return obj.problems.count()
    problem_count.short_description = 'Problems'


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'problem_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    def problem_count(self, obj):
        return obj.problems.count()
    problem_count.short_description = 'Problems'


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'difficulty', 'source_platform', 'tag_list', 'company_list', 'created_at')
    list_filter = ('difficulty', 'source_platform', 'tags', 'companies')
    search_fields = ('title', 'slug', 'description', 'tags__name', 'companies__name')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags', 'companies')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('title',)

    def tag_list(self, obj):
        return ', '.join([t.name for t in obj.tags.all()[:5]])
    tag_list.short_description = 'Tags'

    def company_list(self, obj):
        return ', '.join([c.name for c in obj.companies.all()[:5]])
    company_list.short_description = 'Companies'


@admin.register(UserProblemProgress)
class UserProblemProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'status', 'current_box', 'next_review_date', 'times_solved', 'times_attempted', 'last_solved')
    list_filter = ('status', 'current_box', 'problem__difficulty', 'problem__tags', 'problem__companies')
    search_fields = ('user__username', 'problem__title', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'reviews_count')
    raw_id_fields = ('user', 'problem')
    ordering = ('-updated_at',)


@admin.register(ReviewHistory)
class ReviewHistoryAdmin(admin.ModelAdmin):
    list_display = ('progress', 'old_box', 'new_box', 'action', 'created_at')
    list_filter = ('action', 'old_box', 'new_box')
    search_fields = ('progress__user__username', 'progress__problem__title', 'notes')
    readonly_fields = ('created_at',)
    raw_id_fields = ('progress',)
    ordering = ('-created_at',)


@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'problems_solved', 'problems_attempted', 'total_time_minutes', 'by_topic')
    list_filter = ('user', 'date')
    search_fields = ('user__username',)
    readonly_fields = ('by_topic',)
    raw_id_fields = ('user',)
    ordering = ('-date',)


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_streak', 'longest_streak', 'last_solved_date')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_date', 'problems_per_day', 'is_active', 'created_at', 'day_count')
    list_filter = ('is_active', 'problems_per_day')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def day_count(self, obj):
        return obj.days.count()
    day_count.short_description = 'Days'


@admin.register(StudyPlanDay)
class StudyPlanDayAdmin(admin.ModelAdmin):
    list_display = ('plan', 'date', 'focus_topic', 'difficulty_target', 'reason', 'problem_count')
    list_filter = ('plan', 'difficulty_target', 'focus_topic')
    search_fields = ('plan__user__username', 'focus_topic', 'reason', 'problems__title')
    filter_horizontal = ('problems',)
    raw_id_fields = ('plan',)
    ordering = ('date',)

    def problem_count(self, obj):
        return obj.problems.count()
    problem_count.short_description = 'Problems'