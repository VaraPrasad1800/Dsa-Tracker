import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('./context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    loading: false,
    user: { id: 1, username: 'testuser', email: 'test@example.com' },
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }) => <div>{children}</div>,
}));

vi.mock('./context/ThemeContext', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
  ThemeProvider: ({ children }) => <div>{children}</div>,
}));

vi.mock('./context/TagContext', () => ({
  TagProvider: ({ children }) => <div>{children}</div>,
  useTags: () => ({ showTags: true, setShowTags: vi.fn() }),
}));

vi.mock('./api/client', () => ({
  problemsApi: {
    getProblems: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
    getProblem: vi.fn().mockResolvedValue({ data: {} }),
    getTags: vi.fn().mockResolvedValue({ data: [] }),
    getCompanies: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
    getCompanyProblems: vi.fn().mockResolvedValue({ data: { count: 0, results: [], company: { name: 'Google' } } }),
  },
  progressApi: {
    getStats: vi.fn().mockResolvedValue({ data: {} }),
  },
  spacedRepetitionApi: {
    getStats: vi.fn().mockResolvedValue({ data: { due_today_count: 0 } }),
    getDueToday: vi.fn().mockResolvedValue({ data: [] }),
  },
  analyticsApi: {
    getHeatmap: vi.fn().mockResolvedValue({ data: {} }),
    getTopicBreakdown: vi.fn().mockResolvedValue({ data: [] }),
    getStreaks: vi.fn().mockResolvedValue({ data: {} }),
    getDifficultyBreakdown: vi.fn().mockResolvedValue({ data: {} }),
    getTimeline: vi.fn().mockResolvedValue({ data: [] }),
  },
  interviewApi: {
    getSessions: vi.fn().mockResolvedValue({ data: { sessions: [] } }),
  },
  setNavigateToLogin: vi.fn(),
}));

import CompanyProblemsPage from './pages/CompanyProblemsPage';
import CompaniesPage from './pages/CompaniesPage';

describe('App Routing & Deep Linking', () => {
  let queryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it('renders CompanyProblemsPage with companySlug param on deep link /companies/:companySlug', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/companies/google']}>
          <Routes>
            <Route path="/companies/:companySlug" element={<CompanyProblemsPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Google Problem Bank/i)).toBeInTheDocument();
  });
});
