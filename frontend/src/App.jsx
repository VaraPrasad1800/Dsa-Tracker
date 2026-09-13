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
  return isAuthenticated ? <Navigate to="/" replace /> : <Outlet />;
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

function AppContent() {
  const [activeTab, setActiveTab] = useState('problems');
  const [activeTopicFilter, setActiveTopicFilter] = useState('');
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [targetProblemId, setTargetProblemId] = useState(null);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(220);

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

  const handleSelectTopicFromAnalytics = (topicName) => {
    setActiveTopicFilter(topicName);
    setActiveTab('problems');
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab !== 'companies') setSelectedCompany(null);
    if (tab !== 'problems') setTargetProblemId(null);
  };

  const handleSolveProblem = (prob) => {
    const pId = typeof prob === 'object' ? prob.id : prob;
    setTargetProblemId(pId);
    setActiveTab('problems');
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ background: 'var(--bg-primary)' }}
    >
      {/* Sidebar Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        dueCount={dueCount}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
      />

      {/* Main content — offset by sidebar width on desktop */}
      <div className="flex-1 flex flex-col min-h-screen lg:pl-[220px] transition-all duration-300">
        {/* Reminder Banner */}
        <ReminderBanner
          dueCount={dueCount}
          onStartReview={() => handleTabChange('review')}
        />

        {/* Content Area */}
        <main className="flex-1 px-4 sm:px-6 lg:px-8 pb-20 lg:pb-6">
          <AnimatePresence mode="wait">
            {activeTab === 'problems' && (
              <PageWrapper key="problems">
                <ProblemsPage
                  activeTopicFilter={activeTopicFilter}
                  onSelectTopicFilter={setActiveTopicFilter}
                  initialProblemId={targetProblemId}
                />
              </PageWrapper>
            )}

            {activeTab === 'challenges' && (
              <PageWrapper key="challenges">
                <ChallengesPage onSolve={handleSolveProblem} />
              </PageWrapper>
            )}

            {activeTab === 'interview' && (
              <PageWrapper key="interview">
                <InterviewModePage
                  onNavigateToProblem={handleSolveProblem}
                />
              </PageWrapper>
            )}

            {activeTab === 'achievements' && (
              <PageWrapper key="achievements">
                <AchievementsPage />
              </PageWrapper>
            )}

            {activeTab === 'companies' && !selectedCompany && (
              <PageWrapper key="companies">
                <CompaniesPage onSelectCompany={setSelectedCompany} />
              </PageWrapper>
            )}

            {activeTab === 'companies' && selectedCompany && (
              <PageWrapper key="company-problems">
                <CompanyProblemsPage
                  company={selectedCompany}
                  onBack={() => setSelectedCompany(null)}
                  onNavigateToProblems={() => handleTabChange('problems')}
                  onSolve={handleSolveProblem}
                />
              </PageWrapper>
            )}

            {activeTab === 'review' && (
              <PageWrapper key="review">
                <TodaysReviewPage
                  onNavigateToProblems={() => handleTabChange('problems')}
                  onSolve={handleSolveProblem}
                />
              </PageWrapper>
            )}

            {activeTab === 'analytics' && (
              <PageWrapper key="analytics">
                <AnalyticsPage onSelectFilterTopic={handleSelectTopicFromAnalytics} />
              </PageWrapper>
            )}

            {activeTab === 'study-plan' && (
              <PageWrapper key="study-plan">
                <StudyPlanPage onSolve={handleSolveProblem} />
              </PageWrapper>
            )}
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
        activeTab={activeTab}
        setActiveTab={handleTabChange}
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
          <Route path="/" element={<AppContent />} />
          <Route path="problems/:id/solution" element={<SolutionPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
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