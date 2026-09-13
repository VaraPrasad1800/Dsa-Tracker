from rest_framework.throttling import UserRateThrottle


class JudgeRunThrottle(UserRateThrottle):
    """Throttle for /api/run-code/ endpoint: 10 requests per minute per user."""
    scope = 'judge_run'


class JudgeSubmitThrottle(UserRateThrottle):
    """Throttle for /api/submit/ endpoint: 5 requests per minute per user."""
    scope = 'judge_submit'
