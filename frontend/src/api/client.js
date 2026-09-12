import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage keys
export const ACCESS_TOKEN_KEY = 'dsa_access_token';
export const REFRESH_TOKEN_KEY = 'dsa_refresh_token';
export const USER_KEY = 'dsa_user';

export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY);

// Attach JWT access token to every request (no demo-user fallback).
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh: on a 401, try once with the refresh token, retry the original
// request, and only then treat the session as expired.
let refreshPromise = null;

// Injectable navigate-to-login callback (set by App).
// Falls back to a full page reload only if the React tree is not yet mounted.
let navigateToLogin = null;

export const setNavigateToLogin = (fn) => {
  navigateToLogin = fn;
};

const redirectToLogin = () => {
  if (navigateToLogin) {
    navigateToLogin('/login');
  } else if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login';
  }
};

const clearSession = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

const tryRefresh = async () => {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await axios.create({
          baseURL: API_BASE_URL,
          headers: { 'Content-Type': 'application/json' },
        }).post('/auth/refresh-token/', { refresh_token: refresh });
        localStorage.setItem(ACCESS_TOKEN_KEY, res.data.access_token);
        localStorage.setItem(REFRESH_TOKEN_KEY, res.data.refresh_token);
        return true;
      } catch (err) {
        clearSession();
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    // Only attempt refresh on a real 401 from an API call, and only once per request.
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true;
      const refreshed = await tryRefresh();
      if (refreshed) {
        const token = getAccessToken();
        original.headers['Authorization'] = `Bearer ${token}`;
        return api(original);
      }
      redirectToLogin();
    }
    return Promise.reject(error);
  }
);

export const problemsApi = {
  getProblems: (params) => api.get('/problems/', { params }),
  getProblem: (id) => api.get(`/problems/${id}/`),
  getProblemSolution: (id) => api.get(`/problems/${id}/solution/`),
  getTags: () => api.get('/problems/tags/'),
  getCompanies: () => api.get('/problems/companies/'),
  getCompanyProblems: (companyId, params) => api.get(`/problems/by-company/${companyId}/`, { params }),
};

export const bookmarksApi = {
  toggle: (problemId) => api.post('/bookmarks/toggle/', { problem_id: problemId }),
  list: () => api.get('/bookmarks/'),
};

export const progressApi = {
  saveProgress: (data) => api.post('/user-progress/', data),
  patchProgress: (id, data) => api.patch(`/user-progress/${id}/`, data),
  getStats: () => api.get('/user-progress/stats/'),
  getHistory: (id) => api.get(`/user-progress/${id}/history/`),
};

export const spacedRepetitionApi = {
  getDueToday: () => api.get('/user-progress/due-today/'),
  getStats: () => api.get('/spaced-repetition/stats/'),
};

export const analyticsApi = {
  getDashboard: () => api.get('/analytics/dashboard/'),
  getHeatmap: (year) => api.get('/analytics/heatmap/', { params: { year } }),
  getTopicBreakdown: () => api.get('/analytics/topic-breakdown/'),
  getStreaks: () => api.get('/analytics/streaks/'),
  getDifficultyBreakdown: () => api.get('/analytics/difficulty-breakdown/'),
  getTimeline: (days = 90) => api.get('/analytics/timeline/', { params: { days } }),
};

export const remindersApi = {
  getDigest: () => api.get('/reminders/digest/'),
};

export const studyPlanApi = {
  generate: (data) => api.post('/study-plans/generate/', data),
  getActive: () => api.get('/study-plans/active/'),
  getDetail: (id) => api.get(`/study-plans/${id}/`),
  deactivate: (id) => api.patch(`/study-plans/${id}/deactivate/`),
  getProgress: (id) => api.get(`/study-plans/${id}/progress/`),
};

export const authApi = {
  signup: (data) => api.post('/auth/signup/', data),
  login: (data) => api.post('/auth/login/', data),
  getMe: () => api.get('/auth/me/'),
  verify: () => api.get('/auth/verify/'),
  verifyEmail: (token) => api.post('/auth/verify-email/', { token }),
  resendVerification: (email) => api.post('/auth/resend-verification/', { email }),
  forgotPassword: (email) => api.post('/auth/forgot-password/', { email }),
  resetPassword: (token, newPassword) =>
    api.post('/auth/reset-password/', { token, new_password: newPassword }),
  refreshToken: (refreshToken) => api.post('/auth/refresh-token/', { refresh_token: refreshToken }),
};

export const exportApi = {
  getExportProgress: (format = 'json') => api.get('/export/progress/', {
    params: { format },
    responseType: 'blob',
  }),
};

export const judgeApi = {
  runCode: (data) => api.post('/run-code/', data),
  submitCode: (data) => api.post('/submit/', data),
  getLanguages: () => api.get('/languages/'),
  getTemplate: (problemId, language) => api.get(`/problems/${problemId}/language-template/`, { params: { language } }),
  getTestCases: (problemId) => api.get(`/problems/${problemId}/test-cases/`),
  getSubmissions: (problemId) => api.get(`/problems/${problemId}/submissions/`),
  getSubmissionDetail: (id) => api.get(`/submissions/${id}/`),
};

export const challengesApi = {
  getChallenges: () => api.get('/challenges/'),
  createChallenge: (data) => api.post('/challenges/', data),
  getChallenge: (id) => api.get(`/challenges/${id}/`),
  cancelChallenge: (id) => api.delete(`/challenges/${id}/`),
  completeChallenge: (id) => api.post(`/challenges/${id}/complete/`),
};

export const pointsApi = {
  getPoints: () => api.get('/points/'),
};

export const achievementsApi = {
  getAchievements: () => api.get('/achievements/'),
};

export const notificationsApi = {
  getNotifications: (params) => api.get('/notifications/', { params }),
  markRead: (id) => api.post(`/notifications/${id}/read/`),
  markAllRead: () => api.post('/notifications/read-all/'),
};

export const interviewApi = {
  getSessions: () => api.get('/interview-sessions/'),
  startSession: (data) => api.post('/interview-sessions/', data),
  getSession: (id) => api.get(`/interview-sessions/${id}/`),
  endSession: (id) => api.post(`/interview-sessions/${id}/end/`),
  solveProblem: (sessionId, problemId) => api.post(`/interview-sessions/${sessionId}/problems/${problemId}/solve/`),
};

export const extendedAnalyticsApi = {
  getMastery: () => api.get('/analytics/mastery/'),
  getRevisionQueue: () => api.get('/analytics/revision-queue/'),
  getCompanyTrack: (slug) => api.get(`/analytics/company-track/${slug}/`),
};

export default api;