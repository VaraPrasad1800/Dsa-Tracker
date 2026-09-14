import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { TagProvider } from './context/TagContext';
import { spacedRepetitionApi, setNavigateToLogin } from './api/client';
import Navbar from './components/Navbar';
import ReminderBanner from './components/ReminderBanner';
import MobileNav from './components/common/MobileNav';
import ErrorBoundary from './components/common/ErrorBoundary';
import { AppToaster, toast } from './components/common/Toast';

import ProblemsPage from './pages/ProblemsPage';
import CompaniesPage from './pages/CompaniesPage';
import CompanyProblemsPage from './pages/CompanyProblemsPage';
import TodaysReviewPage from './pages/TodaysReviewPage';
import AnalyticsPage from './pages/AnalyticsPage';
import StudyPlanPage from './pages/StudyPlanPage';
import SolutionPage from './pages/SolutionPage';
import ChallengesPage from './pages/ChallengesPage';
import InterviewModePage from './pages/InterviewModePage';
import AchievementsPage from './pages/AchievementsPage';
import KeyboardShortcutsModal from './components/problems/KeyboardShortcutsModal';

// Auth pages
import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import VerifyEmailPage from './pages/auth/VerifyEmailPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 2,
    },
  },
});

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace state={{ from: window.location.pathname }} />;
}

function PublicRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? <Navigate to="/problems" replace /> : <Outlet />;
}

function NavigateToLogin() {
  const navigate = useNavigate();
  React.useEffect(() => {
    setNavigateToLogin((to) => navigate(to, { replace: true }));
    return () => setNavigateToLogin(null);
  }, [navigate]);
  return null;
}

// Page transition wrapper
const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
};
const pageTransition = { duration: 0.22, ease: [0.4, 0, 0.2, 1] };

function PageWrapper({ children }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
    >
      {children}
    </motion.div>
  );
}

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);

  const { data: dueData } = useQuery({
    queryKey: ['due-today-count'],
    queryFn: async () => {
      const res = await spacedRepetitionApi.getStats();
      return res.data;
    },
    refetchInterval: 30000,
  });

  const dueCount = dueData?.due_today_count || 0;

  // Show streak milestone toasts
  useEffect(() => {
    if (dueData?.current_streak && dueData.current_streak > 0 && dueData.current_streak % 7 === 0) {
      toast.success(`🔥 ${dueData.current_streak}-day streak! Keep it up!`);
    }
  }, [dueData?.current_streak]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      if (e.key === '?') setIsShortcutsOpen(true);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div
      className="min-h-screen flex"
      style={{ background: 'var(--bg-primary)' }}
    >
      {/* Sidebar Navigation */}
      <Navbar
        dueCount={dueCount}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
      />

      {/* Main content — dynamically shares flex width with sticky sidebar */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0 transition-all duration-300">
        {/* Reminder Banner */}
        <ReminderBanner
          dueCount={dueCount}
          onStartReview={() => navigate('/today-review')}
        />

        {/* Content Area */}
        <main className="flex-1 px-4 sm:px-6 lg:px-6 pb-20 lg:pb-6">
          <AnimatePresence mode="wait">
            <PageWrapper key={location.pathname}>
              <Outlet />
            </PageWrapper>
          </AnimatePresence>
        </main>

        {/* Footer */}
        <footer
          className="py-4 text-center text-xs pb-20 lg:pb-4 border-t"
          style={{ borderColor: 'rgba(255,255,255,0.04)', color: '#334155' }}
        >
          DSA Tracker • Leitner SRS + AI Study Planning • Django & React
        </footer>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileNav
        dueCount={dueCount}
      />

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
    </div>
  );
}

function ProblemsRoute() {
  return <ProblemsPage />;
}

function ChallengesRoute() {
  const navigate = useNavigate();
  return (
    <ChallengesPage
      onSolve={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function InterviewModeRoute() {
  const navigate = useNavigate();
  return (
    <InterviewModePage
      onNavigateToProblem={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function CompaniesRoute() {
  return <CompaniesPage />;
}

function CompanyProblemsRoute() {
  const navigate = useNavigate();
  return (
    <CompanyProblemsPage
      onBack={() => navigate('/companies')}
      onNavigateToProblems={() => navigate('/problems')}
      onSolve={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function TodaysReviewRoute() {
  const navigate = useNavigate();
  return (
    <TodaysReviewPage
      onNavigateToProblems={() => navigate('/problems')}
      onSolve={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function AnalyticsRoute() {
  const navigate = useNavigate();
  return (
    <AnalyticsPage
      onSelectFilterTopic={(topicName) => {
        navigate(`/problems?topic=${encodeURIComponent(topicName)}`, {
          state: { activeTopicFilter: topicName },
        });
      }}
      onSelectProblem={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function AchievementsRoute() {
  return <AchievementsPage />;
}

function StudyPlanRoute() {
  const navigate = useNavigate();
  return (
    <StudyPlanPage
      onSolve={(prob) => {
        const id = typeof prob === 'object' ? prob.id : prob;
        navigate('/problems', { state: { targetProblemId: id } });
      }}
    />
  );
}

function RouteErrorBoundary({ children }) {
  const location = useLocation();
  return (
    <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>
  );
}

function MainRoutes() {
  return (
    <RouteErrorBoundary>
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/problems" replace />} />
            <Route path="/problems" element={<ProblemsRoute />} />
            <Route path="/companies" element={<CompaniesRoute />} />
            <Route path="/companies/:companySlug" element={<CompanyProblemsRoute />} />
            <Route path="/challenges" element={<ChallengesRoute />} />
            <Route path="/interview-mode" element={<InterviewModeRoute />} />
            <Route path="/today-review" element={<TodaysReviewRoute />} />
            <Route path="/analytics" element={<AnalyticsRoute />} />
            <Route path="/achievements" element={<AchievementsRoute />} />
            <Route path="/study-plan" element={<StudyPlanRoute />} />
            <Route path="/problems/:id/solution" element={<SolutionPage />} />

            {/* Backwards-compatibility aliases */}
            <Route path="/interview" element={<Navigate to="/interview-mode" replace />} />
            <Route path="/review" element={<Navigate to="/today-review" replace />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/problems" replace />} />
      </Routes>
    </RouteErrorBoundary>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TagProvider>
              <BrowserRouter>
                <NavigateToLogin />
                <MainRoutes />
                <AppToaster />
              </BrowserRouter>
            </TagProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}