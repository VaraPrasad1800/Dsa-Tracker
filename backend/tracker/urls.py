from django.urls import path
from tracker import views

urlpatterns = [
    # Phase 1: Problem Bank & Progress
    path('problems/', views.ProblemListView.as_view(), name='problem-list'),
    path('problems/practice/', views.TopicPracticeView.as_view(), name='topic-practice'),
    path('problems/tags/', views.TagListView.as_view(), name='tag-list'),
    path('problems/companies/', views.CompanyListView.as_view(), name='company-list'),
    path('problems/by-company/<str:company_id>/', views.ProblemByCompanyView.as_view(), name='problem-by-company'),
    path('problems/<uuid:pk>/', views.ProblemDetailView.as_view(), name='problem-detail'),
    path('problems/<uuid:pk>/solution/', views.ProblemSolutionView.as_view(), name='problem-solution'),

    # V2: Judge — per-problem endpoints
    path('problems/<uuid:pk>/submissions/', views.ProblemSubmissionsView.as_view(), name='problem-submissions'),
    path('problems/<uuid:pk>/test-cases/', views.ProblemTestCasesView.as_view(), name='problem-test-cases'),
    path('problems/<uuid:pk>/language-template/', views.LanguageTemplateView.as_view(), name='problem-language-template'),

    path('user-progress/', views.UserProgressView.as_view(), name='user-progress-create'),
    path('user-progress/stats/', views.UserProgressStatsView.as_view(), name='user-progress-stats'),
    path('user/focus-topics/', views.UserFocusTopicsView.as_view(), name='user-focus-topics'),
    path('user-progress/due-today/', views.DueTodayView.as_view(), name='due-today'),
    path('user-progress/<uuid:pk>/', views.UserProgressDetailView.as_view(), name='user-progress-detail'),
    path('user-progress/<uuid:pk>/history/', views.UserProgressHistoryView.as_view(), name='user-progress-history'),

    # Phase 2: Spaced Repetition Stats
    path('spaced-repetition/stats/', views.SpacedRepetitionStatsView.as_view(), name='spaced-repetition-stats'),

    # Phase 3: Analytics
    path('analytics/heatmap/', views.HeatmapView.as_view(), name='analytics-heatmap'),
    path('analytics/topic-breakdown/', views.TopicBreakdownView.as_view(), name='analytics-topic-breakdown'),
    path('analytics/streaks/', views.StreaksView.as_view(), name='analytics-streaks'),
    path('analytics/difficulty-breakdown/', views.DifficultyBreakdownView.as_view(), name='analytics-difficulty-breakdown'),
    path('analytics/timeline/', views.TimelineView.as_view(), name='analytics-timeline'),
    path('analytics/dashboard/', views.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),

    # V2: Enhanced Analytics
    path('analytics/mastery/', views.TopicMasteryView.as_view(), name='analytics-mastery'),
    path('analytics/revision-queue/', views.RevisionQueueView.as_view(), name='analytics-revision-queue'),
    path('analytics/company-track/<str:company_slug>/', views.CompanyTrackView.as_view(), name='analytics-company-track'),

    # Phase 4: Reminders
    path('reminders/digest/', views.DailyDigestView.as_view(), name='reminders-digest'),

    # Phase 5: Study Plans
    path('study-plans/generate/', views.StudyPlanGenerateView.as_view(), name='study-plan-generate'),
    path('study-plans/active/', views.StudyPlanActiveView.as_view(), name='study-plan-active'),
    path('study-plans/<uuid:pk>/', views.StudyPlanDetailView.as_view(), name='study-plan-detail'),
    path('study-plans/<uuid:pk>/deactivate/', views.StudyPlanDeactivateView.as_view(), name='study-plan-deactivate'),
    path('study-plans/<uuid:pk>/progress/', views.StudyPlanProgressView.as_view(), name='study-plan-progress'),

    # Export
    path('export/progress/', views.ExportProgressView.as_view(), name='export-progress'),

    # Authentication: JWT + Email Verification + Password Reset
    path('auth/signup/', views.RegisterView.as_view(), name='auth-signup'),
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/verify/', views.VerifyTokenView.as_view(), name='auth-verify'),
    path('auth/verify-email/', views.VerifyEmailView.as_view(), name='auth-verify-email'),
    path('auth/resend-verification/', views.ResendVerificationView.as_view(), name='auth-resend-verification'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='auth-reset-password'),
    path('auth/refresh-token/', views.RefreshTokenView.as_view(), name='auth-refresh-token'),
    path('auth/me/', views.CurrentUserView.as_view(), name='auth-me'),

    # Bookmarks
    path('bookmarks/toggle/', views.BookmarkToggleView.as_view(), name='bookmark-toggle'),
    path('bookmarks/', views.BookmarkListView.as_view(), name='bookmark-list'),

    # V2: Online Judge
    path('run-code/', views.RunCodeView.as_view(), name='run-code'),
    path('submit/', views.SubmitCodeView.as_view(), name='submit-code'),
    path('languages/', views.LanguagesView.as_view(), name='languages'),
    path('submissions/<uuid:pk>/', views.SubmissionDetailView.as_view(), name='submission-detail'),

    # V2: Challenges
    path('challenges/', views.ChallengeListView.as_view(), name='challenge-list'),
    path('challenges/<uuid:pk>/', views.ChallengeDetailView.as_view(), name='challenge-detail'),
    path('challenges/<uuid:pk>/complete/', views.ChallengeCompleteView.as_view(), name='challenge-complete'),

    # V2: Points & Achievements
    path('points/', views.UserPointsView.as_view(), name='user-points'),
    path('achievements/', views.AchievementListView.as_view(), name='achievement-list'),

    # V2: Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/read-all/', views.NotificationReadAllView.as_view(), name='notification-read-all'),
    path('notifications/<uuid:pk>/read/', views.NotificationReadView.as_view(), name='notification-read'),

    # V2: Interview Simulation
    path('interview-sessions/', views.InterviewSessionListView.as_view(), name='interview-session-list'),
    path('interview-sessions/<uuid:pk>/', views.InterviewSessionDetailView.as_view(), name='interview-session-detail'),
    path('interview-sessions/<uuid:pk>/end/', views.InterviewSessionEndView.as_view(), name='interview-session-end'),
    path('interview-sessions/<uuid:session_pk>/problems/<uuid:problem_pk>/solve/',
         views.InterviewProblemSolveView.as_view(), name='interview-problem-solve'),

    # V2: DSA Patterns
    path('patterns/', views.PatternListView.as_view(), name='pattern-list'),
]
