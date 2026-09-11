import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class Tag(models.Model):
    CATEGORY_CHOICES = [
        ('data_structure', 'Data Structure'),
        ('algorithm', 'Algorithm'),
        ('technique', 'Technique'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    color = models.CharField(max_length=7, blank=True, default='', help_text='Hex color for badge styling, e.g. #3b82f6')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='algorithm')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    description = models.TextField(blank=True, default='')
    tags = models.ManyToManyField(Tag, related_name='problems', blank=True)
    companies = models.ManyToManyField(Company, related_name='problems', blank=True)
    source_url = models.URLField(max_length=500, blank=True, default='')
    source_platform = models.CharField(max_length=50, default='LeetCode')
    time_limit_minutes = models.IntegerField(null=True, blank=True)
    leetcode_id = models.IntegerField(null=True, blank=True, help_text='LeetCode problem ID number')
    is_premium = models.BooleanField(default=False, help_text='True if LeetCode Premium-only problem')
    frequency = models.IntegerField(default=0, help_text='How often this problem appears in interviews (0-100)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} ({self.difficulty})'


class Solution(models.Model):
    """Cached solution scraped from leetcode.ca."""

    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('javascript', 'JavaScript'),
        ('c', 'C'),
        ('go', 'Go'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE, related_name='cached_solution')
    question_number = models.IntegerField(null=True, blank=True, help_text='LeetCode problem number')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='', help_text='Scraped problem statement description')
    code = models.TextField()
    language = models.CharField(max_length=30, choices=LANGUAGE_CHOICES, default='python')
    explanation = models.TextField(blank=True, default='')
    time_complexity = models.CharField(max_length=100, blank=True, default='')
    space_complexity = models.CharField(max_length=100, blank=True, default='')
    # source_url = the /all/{id}.html overview page (Page 1 starting point)
    source_url = models.URLField(max_length=500, blank=True, default='')
    # solution_source_url = the dedicated solution blog post URL discovered on Page 1
    solution_source_url = models.URLField(
        max_length=500, blank=True, default='',
        help_text='Dedicated solution page URL on leetcode.ca (e.g. /YYYY-MM-DD-{id}-slug/)'
    )
    last_fetched_at = models.DateTimeField(auto_now=True)
    fetch_failed = models.BooleanField(default=False)
    fetch_error = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-last_fetched_at']

    def __str__(self):
        return f'Solution for {self.problem.title}'

    @property
    def is_fresh(self):
        """Return True if this is a *successful* cache not older than 7 days."""
        from django.utils import timezone
        if self.fetch_failed:
            return False
        return (timezone.now() - self.last_fetched_at) < timezone.timedelta(days=7)

    @property
    def should_retry_failed(self):
        """
        Temporary failures should be retried after 1 hour, not permanently blocked.
        Returns True when a failed record is old enough to warrant a new fetch attempt.
        """
        from django.utils import timezone
        if not self.fetch_failed:
            return False
        return (timezone.now() - self.last_fetched_at) > timezone.timedelta(hours=1)

    @property
    def is_available(self):
        """Return True if we have a successful cache (not a failure)."""
        return not self.fetch_failed


class CompanyProblem(models.Model):
    """
    Represents the appearance of a LeetCode problem in a specific company's list
    and time period (e.g. Google - Thirty Days / Three Months / All), along with
    frequency and acceptance rate from the CSV data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_problem_records')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='company_problem_records')
    time_period = models.CharField(max_length=100, blank=True, default='', help_text='e.g. Thirty Days, Three Months, Six Months, More Than Six Months, All')
    frequency = models.FloatField(default=0.0, help_text='Interview frequency percentage from CSV')
    acceptance_rate = models.FloatField(null=True, blank=True, help_text='Acceptance rate from CSV')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'problem', 'time_period')
        ordering = ['-frequency', 'problem__title']

    def __str__(self):
        return f'{self.company.name} - {self.problem.title} ({self.time_period}, freq={self.frequency})'


class UserProblemProgress(models.Model):
    STATUS_CHOICES = [
        ('UNSOLVED', 'Unsolved'),
        ('SOLVED', 'Solved'),
        ('NEEDS_REVISIT', 'Needs Revisit'),
        ('SKIPPED', 'Skipped'),
    ]

    CODE_LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('javascript', 'JavaScript'),
        ('c', 'C'),
        ('go', 'Go'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_progresses')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='user_progresses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNSOLVED')
    times_solved = models.IntegerField(default=0)
    times_attempted = models.IntegerField(default=0)
    last_attempted = models.DateTimeField(null=True, blank=True)
    last_solved = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    code_solution = models.TextField(blank=True, default='')
    code_language = models.CharField(max_length=30, choices=CODE_LANGUAGE_CHOICES, default='python')

    # Phase 2: Leitner spaced repetition fields
    current_box = models.IntegerField(default=1)  # range 1-5
    next_review_date = models.DateTimeField(null=True, blank=True)
    reviews_count = models.IntegerField(default=0)

    # Time tracking
    total_time_spent_minutes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'problem')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} - {self.problem.title} [{self.status}] (Box {self.current_box})'

class ReviewHistory(models.Model):
    progress = models.ForeignKey(UserProblemProgress, on_delete=models.CASCADE, related_name='histories')
    old_box = models.IntegerField()
    new_box = models.IntegerField()
    action = models.CharField(max_length=30)
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Box {self.old_box} -> {self.new_box} ({self.action}) on {self.created_at}'

class DailyStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_stats')
    date = models.DateField()
    problems_solved = models.IntegerField(default=0)
    problems_attempted = models.IntegerField(default=0)
    total_time_minutes = models.IntegerField(default=0)
    by_topic = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} on {self.date}: {self.problems_solved} solved'

class UserStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_solved_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username}: current={self.current_streak}, longest={self.longest_streak}'

class UserProfile(models.Model):
    """Extended user profile for email verification, password reset, and bookmarks."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_email_verified = models.BooleanField(default=False)

    # Email verification token (hashed with SHA-256)
    email_verification_token_hash = models.CharField(max_length=64, blank=True, default='')
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    # Password reset token (hashed with SHA-256)
    password_reset_token_hash = models.CharField(max_length=64, blank=True, default='')
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)

    # Bookmarks
    bookmarked_problems = models.ManyToManyField(Problem, related_name='bookmarked_by', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user.username} (verified={self.is_email_verified})'

class StudyPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    target_date = models.DateField()
    problems_per_day = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Plan for {self.user.username} until {self.target_date} ({self.problems_per_day}/day)'

class StudyPlanDay(models.Model):
    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='days')
    date = models.DateField()
    problems = models.ManyToManyField(Problem, related_name='plan_days', blank=True)
    focus_topic = models.CharField(max_length=100, null=True, blank=True)
    difficulty_target = models.CharField(max_length=20, default='Medium')
    reason = models.CharField(max_length=255)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.date}: {self.reason}'
