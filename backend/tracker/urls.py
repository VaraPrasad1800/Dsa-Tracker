from django.urls import path
from tracker import views

urlpatterns = [
    # Phase 1: Problem Bank & Progress
    path('problems/', views.ProblemListView.as_view(), name='problem-list'),
    path('problems/tags/', views.TagListView.as_view(), name='tag-list'),
    path('problems/companies/', views.CompanyListView.as_view(), name='company-list'),
    path('problems/by-company/<str:company_id>/', views.ProblemByCompanyView.as_view(), name='problem-by-company'),
    path('problems/<uuid:pk>/', views.ProblemDetailView.as_view(), name='problem-detail'),
    path('problems/<uuid:pk>/solution/', views.ProblemSolutionView.as_view(), name='problem-solution'),
    
    path('user-progress/', views.UserProgressView.as_view(), name='user-progress-create'),
    path('user-progress/stats/', views.UserProgressStatsView.as_view(), name='user-progress-stats'),
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

    # Analytics Dashboard
    path('analytics/dashboard/', views.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
]
