import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

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
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, db_index=True)
    description = models.TextField(blank=True, default='')
    tags = models.ManyToManyField(Tag, related_name='problems', blank=True)
    companies = models.ManyToManyField(Company, related_name='problems', blank=True)
    source_url = models.URLField(max_length=500, blank=True, default='')
    source_platform = models.CharField(max_length=50, default='LeetCode')
    time_limit_minutes = models.IntegerField(null=True, blank=True)
    time_limit_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(100),
            MaxValueValidator(15000),
        ],
        help_text="Execution time limit in milliseconds per test case. Fallback to difficulty-aware platform default if unset."
    )
    memory_limit_mb = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(16),
            MaxValueValidator(1024),
        ],
        help_text="Execution memory limit in megabytes per test case. Fallback to platform default if unset."
    )
    question_number = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='Canonical user-facing unique problem number (e.g. 1 for Two Sum, 42 for Trapping Rain Water)'
    )
    leetcode_id = models.IntegerField(null=True, blank=True, help_text='LeetCode problem ID number')
    is_premium = models.BooleanField(default=False, help_text='True if LeetCode Premium-only problem')
    frequency = models.IntegerField(default=0, db_index=True, help_text='How often this problem appears in interviews (0-100)')
    EXECUTION_MODE_CHOICES = [
        ('FUNCTION', 'Function-based'),
        ('STDIN_STDOUT', 'Standard I/O'),
    ]
    execution_mode = models.CharField(
        max_length=20,
        choices=EXECUTION_MODE_CHOICES,
        default='STDIN_STDOUT',
        db_index=True,
        help_text='Whether this problem evaluates a function signature or reads from stdin/stdout'
    )
    input_format = models.TextField(blank=True, default='', help_text='Specification of the input format via stdin')
    output_format = models.TextField(blank=True, default='', help_text='Specification of the output format via stdout')
    function_name = models.CharField(max_length=100, blank=True, default='', help_text='Target function/method name for function-based problems')
    class_name = models.CharField(max_length=100, default='Solution', blank=True, help_text='Class name enclosing the solution method')
    parameters_meta = models.JSONField(default=list, blank=True, help_text='List of parameter definitions [{name: "nums", type: "list[int]"}]')
    return_type = models.CharField(max_length=100, default='', blank=True, help_text='Return type annotation for the method')
    READINESS_CHOICES = [
        ('JUDGE_READY', 'Judge Ready'),
        ('CONFIGURATION_REQUIRED', 'Configuration Required'),
    ]
    is_judge_ready = models.BooleanField(default=False, db_index=True, help_text='True if problem satisfies complete execution contract')
    judge_readiness_status = models.CharField(
        max_length=50,
        choices=READINESS_CHOICES,
        default='CONFIGURATION_REQUIRED',
        db_index=True,
        help_text='Canonical judge readiness status'
    )

    # ---------------------------------------------------------------------------
    # Preparation pipeline status — used by prepare_judge_data management command.
    # Persisted to DB so the pipeline is safely resumable after any interruption.
    # ---------------------------------------------------------------------------
    PREPARATION_STATUS_CHOICES = [
        ('PENDING', 'Pending — not yet processed'),
        ('FETCHING', 'Fetching — network request in progress (or interrupted)'),
        ('NORMALIZING', 'Normalizing — data processing in progress (or interrupted)'),
        ('JUDGE_READY', 'Judge Ready — fully prepared'),
        ('CONFIGURATION_REQUIRED', 'Configuration Required — missing data, not fetchable'),
        ('FAILED', 'Failed — fetch/prepare error, eligible for retry'),
    ]
    preparation_status = models.CharField(
        max_length=30,
        choices=PREPARATION_STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text='Persistent stage of the judge-data preparation pipeline for this problem'
    )
    preparation_error = models.TextField(
        blank=True,
        default='',
        help_text='Last error message from the preparation pipeline, if any'
    )
    preparation_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text='Number of times preparation has been attempted'
    )
    preparation_last_attempted = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the last preparation attempt'
    )
    OUTPUT_CHECKER_CHOICES = [
        ('EXACT', 'Exact match (character-for-character)'),
        ('NORMALIZED', 'Normalized text (whitespace-insensitive)'),
        ('NORMALIZED_TEXT', 'Normalized text (whitespace-insensitive)'),
        ('ALTERNATIVES', 'Multiple Valid Alternatives (pipe-separated)'),
        ('JSON', 'JSON Equality'),
        ('BOOLEAN', 'Boolean (true/false, case-insensitive)'),
        ('INTEGER', 'Integer (numeric equality)'),
        ('FLOAT_WITH_TOLERANCE', 'Float with 1e-5 tolerance'),
        ('ARRAY', 'Ordered Array (space-separated elements)'),
        ('ORDER_INSENSITIVE_ARRAY', 'Order-Insensitive Array (multiset equality)'),
    ]
    output_checker = models.CharField(
        max_length=50,
        choices=OUTPUT_CHECKER_CHOICES,
        default='NORMALIZED',
        help_text='Output validator mode for judging solutions'
    )
    missing_configuration = models.JSONField(
        default=list,
        blank=True,
        help_text='List of missing prerequisites when judge readiness is CONFIGURATION_REQUIRED'
    )
    examples = models.JSONField(default=list, blank=True, help_text='Structured list of problem examples [{input, output, explanation}]')
    constraints = models.JSONField(default=list, blank=True, help_text='Structured list of constraints')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['question_number', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Assign question_number if not set
        if self.question_number is None:
            if self.leetcode_id is not None:
                self.question_number = self.leetcode_id
            else:
                max_num = Problem.objects.aggregate(models.Max('question_number'))['question_number__max'] or 0
                self.question_number = max_num + 1

        super().save(*args, **kwargs)

    def __str__(self):
        if self.question_number:
            return f'#{self.question_number} {self.title} ({self.difficulty})'
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
    code_by_language = models.JSONField(default=dict, blank=True, help_text='Dictionary of language -> code for multi-language solutions')
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

    # Custom focus areas / weak topics chosen by user (max 5 enforced at API layer)
    focus_topics = models.ManyToManyField(Tag, related_name='focused_by_users', blank=True)

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


# ============================================================================
# V2 MODELS — Online Judge, Challenges, Achievements, Interview, Activity
# ============================================================================

class DSAPattern(models.Model):
    """A common DSA problem-solving pattern (e.g. Two Pointers, BFS, DP)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default='')
    problems = models.ManyToManyField(Problem, related_name='patterns', blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class TestCase(models.Model):
    """A single test case for a problem (visible or hidden)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    is_hidden = models.BooleanField(
        default=False,
        help_text='Hidden test cases are NEVER returned to the frontend. '
                  'Only verdict + pass/fail count is returned.'
    )
    input_text = models.TextField(blank=True, default='')
    expected_output = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)
    time_limit_seconds = models.FloatField(null=True, blank=True)
    memory_limit_mb = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['problem', 'is_hidden', 'order']

    def __str__(self):
        kind = 'Hidden' if self.is_hidden else 'Visible'
        return f'{kind} TestCase #{self.order} for {self.problem.title}'


class LanguageTemplate(models.Model):
    """Starter code template for a specific language on a specific problem."""
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('c', 'C'),
        ('cpp', 'C++'),
        ('java', 'Java'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='language_templates')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    starter_code = models.TextField(blank=True, default='')
    harness_code = models.TextField(blank=True, default='', help_text='Driver code appended during execution for function-based problems')

    class Meta:
        unique_together = ('problem', 'language')

    def __str__(self):
        return f'{self.problem.title} — {self.language} template'


class Submission(models.Model):
    """A code submission by a user for a problem."""
    VERDICT_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('WRONG_ANSWER', 'Wrong Answer'),
        ('COMPILE_ERROR', 'Compilation Error'),
        ('RUNTIME_ERROR', 'Runtime Error'),
        ('TLE', 'Time Limit Exceeded'),
        ('MLE', 'Memory Limit Exceeded'),
        ('EXECUTION_ERROR', 'Execution Error'),
        ('SYSTEM_ERROR', 'Internal Error'),
    ]
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('c', 'C'),
        ('cpp', 'C++'),
        ('java', 'Java'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    source_code = models.TextField()
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES, default='PENDING')
    tests_passed = models.IntegerField(default=0)
    tests_total = models.IntegerField(default=0)
    execution_time_ms = models.IntegerField(default=0)
    memory_kb = models.IntegerField(default=0)
    compile_error = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'problem']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.problem.title} [{self.verdict}]'

    @property
    def is_accepted(self):
        return self.verdict == 'ACCEPTED'


class Challenge(models.Model):
    """A timed or deadline-based challenge created by a user."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    TEMPLATE_CHOICES = [
        ('COUNT', 'Count Challenge'),
        ('TIMED', 'Timed Challenge'),
        ('TOPIC', 'Topic Challenge'),
        ('DIFFICULTY', 'Difficulty Challenge'),
        ('COMPANY', 'Company Challenge'),
        ('DEADLINE', 'Deadline Challenge'),
        ('REVIEW', 'Review Challenge'),
        ('CUSTOM', 'Custom Challenge'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenges')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='CUSTOM')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    target_count = models.IntegerField(default=1)
    points = models.IntegerField(default=0)
    bonus_points = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    topic_filter = models.ForeignKey(Tag, null=True, blank=True, on_delete=models.SET_NULL)
    difficulty_filter = models.CharField(max_length=10, blank=True, default='')
    company_filter = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)
    completed_count = models.IntegerField(default=0)
    points_earned = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.title} [{self.status}]'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.end_time and self.status == 'ACTIVE'

    @property
    def time_remaining_seconds(self):
        from django.utils import timezone
        diff = (self.end_time - timezone.now()).total_seconds()
        return max(0, diff)


class ChallengeProblem(models.Model):
    """A problem assigned to a challenge."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='challenge_problems')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('challenge', 'problem')

    def __str__(self):
        status = 'done' if self.completed else 'pending'
        return f'{status}: {self.problem.title} in {self.challenge.title}'


class Achievement(models.Model):
    """A deterministic milestone achievement definition."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500)
    icon = models.CharField(max_length=50, blank=True, default='🏆')
    points = models.IntegerField(default=0)
    required_solve_count = models.IntegerField(null=True, blank=True)
    required_streak_days = models.IntegerField(null=True, blank=True)
    required_difficulty = models.CharField(max_length=10, blank=True, default='')
    required_tag_slug = models.CharField(max_length=120, blank=True, default='')
    required_challenge_count = models.IntegerField(null=True, blank=True)
    required_accepted_count = models.IntegerField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f'{self.icon} {self.name}'


class UserAchievement(models.Model):
    """Records when a user unlocked an achievement (idempotent)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f'{self.user.username} unlocked {self.achievement.name}'


class Notification(models.Model):
    """Per-user in-app notification."""
    TYPE_CHOICES = [
        ('REVIEW_DUE', 'Reviews Due'),
        ('CHALLENGE_EXPIRING', 'Challenge Expiring Soon'),
        ('CHALLENGE_COMPLETED', 'Challenge Completed'),
        ('ACHIEVEMENT_UNLOCKED', 'Achievement Unlocked'),
        ('STREAK_MILESTONE', 'Streak Milestone'),
        ('STUDY_PLAN_BEHIND', 'Study Plan Behind'),
        ('INTERVIEW_RESULT', 'Interview Result'),
        ('SYSTEM', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='SYSTEM')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.title} ({"read" if self.is_read else "unread"})'


class InterviewSession(models.Model):
    """A timed interview simulation session."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ]
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
        ('Mixed', 'Mixed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_sessions')
    duration_minutes = models.IntegerField(default=45)
    num_problems = models.IntegerField(default=2)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    problems_solved = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} interview {self.started_at.date()} [{self.status}]'

    @property
    def elapsed_minutes(self):
        from django.utils import timezone
        end = self.ended_at or timezone.now()
        return int((end - self.started_at).total_seconds() / 60)

    @property
    def deadline(self):
        from datetime import timedelta
        return self.started_at + timedelta(minutes=self.duration_minutes)


class InterviewProblem(models.Model):
    """A problem within an interview session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='interview_problems')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    solved = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    submission = models.ForeignKey(
        Submission, null=True, blank=True, on_delete=models.SET_NULL,
    )

    class Meta:
        unique_together = ('session', 'problem')

    def __str__(self):
        return f'{self.session} — {self.problem.title}'


class ActivityEvent(models.Model):
    """Lightweight activity event log for analytics and audit."""
    EVENT_CHOICES = [
        ('PROBLEM_VIEWED', 'Problem Viewed'),
        ('CODE_RUN', 'Code Run'),
        ('SUBMISSION_CREATED', 'Submission Created'),
        ('SUBMISSION_ACCEPTED', 'Submission Accepted'),
        ('REVIEW_COMPLETED', 'Review Completed'),
        ('PROBLEM_REVISIT', 'Problem Marked Revisit'),
        ('BOOKMARK_ADDED', 'Bookmark Added'),
        ('NOTE_UPDATED', 'Note Updated'),
        ('CHALLENGE_STARTED', 'Challenge Started'),
        ('CHALLENGE_COMPLETED', 'Challenge Completed'),
        ('INTERVIEW_STARTED', 'Interview Started'),
        ('INTERVIEW_COMPLETED', 'Interview Completed'),
        ('ACHIEVEMENT_UNLOCKED', 'Achievement Unlocked'),
        ('POINTS_AWARDED', 'Points Awarded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_events')
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    problem = models.ForeignKey(Problem, null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.event_type} at {self.created_at}'


class UserPoints(models.Model):
    """Running point totals for a user (server-authoritative)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points')
    total = models.IntegerField(default=0)
    weekly = models.IntegerField(default=0)
    challenge_points = models.IntegerField(default=0)
    streak_points = models.IntegerField(default=0)
    last_weekly_reset = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}: {self.total} pts total'


class RefreshToken(models.Model):
    """Stores refresh token hashes for revocation and rotation tracking."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token_hash']),
            models.Index(fields=['user', 'revoked']),
        ]

    def __str__(self):
        status_str = 'Revoked' if self.revoked else 'Active'
        return f'{self.user.username} - {status_str} (expires {self.expires_at})'

