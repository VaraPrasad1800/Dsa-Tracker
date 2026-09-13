import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import InterviewModePage from './InterviewModePage';
import { interviewApi, problemsApi } from '../api/client';

vi.mock('../api/client', () => ({
  interviewApi: {
    getSessions: vi.fn(),
    startSession: vi.fn(),
    endSession: vi.fn(),
    solveProblem: vi.fn(),
  },
  problemsApi: {
    getCompanies: vi.fn(),
  },
}));

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockActiveSession = {
  id: 'session-123',
  status: 'ACTIVE',
  difficulty: 'Medium',
  duration_minutes: 45,
  num_problems: 2,
  company_name: 'Google',
  deadline: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
  problems_solved: 0,
  interview_problems: [
    {
      id: 'ip-1',
      problem: 'prob-1',
      question_number: 1,
      problem_title: 'Two Sum',
      problem_slug: 'two-sum',
      problem_difficulty: 'Easy',
      leetcode_url: 'https://leetcode.com/problems/two-sum/',
      solved: false,
      attempts: 0,
    },
    {
      id: 'ip-2',
      problem: 'prob-2',
      question_number: 15,
      problem_title: '3Sum',
      problem_slug: '3sum',
      problem_difficulty: 'Medium',
      leetcode_url: 'https://leetcode.com/problems/3sum/',
      solved: true,
      attempts: 1,
    },
  ],
};

const renderWithQueryClient = (ui) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

describe('InterviewModePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    problemsApi.getCompanies.mockResolvedValue({ data: [] });
  });

  it('renders interview mode without crashing when no active session', async () => {
    interviewApi.getSessions.mockResolvedValue({ data: { sessions: [] } });

    renderWithQueryClient(<InterviewModePage />);

    expect(await screen.findByText('Interview Simulation Mode')).toBeInTheDocument();
    expect(screen.getByText('Start New Interview Simulation')).toBeInTheDocument();
  });

  it('renders active interview session with problems, Open on LeetCode links, and Mark as Solved', async () => {
    interviewApi.getSessions.mockResolvedValue({
      data: { sessions: [mockActiveSession] },
    });

    renderWithQueryClient(<InterviewModePage />);

    // Check problems are displayed
    expect(await screen.findByText('Two Sum')).toBeInTheDocument();
    expect(screen.getByText('3Sum')).toBeInTheDocument();

    // Check Open on LeetCode links
    const leetcodeLinks = screen.getAllByRole('link', { name: /Open on LeetCode/i });
    expect(leetcodeLinks).toHaveLength(2);
    expect(leetcodeLinks[0]).toHaveAttribute('href', 'https://leetcode.com/problems/two-sum/');
    expect(leetcodeLinks[0]).toHaveAttribute('target', '_blank');

    // Check Problem #1 is unsolved and has Mark as Solved button
    const markSolvedBtn = screen.getByRole('button', { name: /Mark as Solved/i });
    expect(markSolvedBtn).toBeInTheDocument();

    // Check Problem #2 is already solved
    expect(screen.getAllByText('Solved ✓').length).toBeGreaterThanOrEqual(1);
  });

  it('triggers solveProblem API and updates UI immediately when Mark as Solved is clicked', async () => {
    interviewApi.getSessions.mockResolvedValue({
      data: { sessions: [mockActiveSession] },
    });
    interviewApi.solveProblem.mockResolvedValue({
      data: { solved: true, problems_solved: 1 },
    });

    renderWithQueryClient(<InterviewModePage />);

    const markSolvedBtn = await screen.findByRole('button', { name: /Mark as Solved/i });
    fireEvent.click(markSolvedBtn);

    await waitFor(() => {
      expect(interviewApi.solveProblem).toHaveBeenCalledWith('session-123', 'prob-1');
    });

    // After solving, both problems should show as solved
    await waitFor(() => {
      const solvedBadges = screen.getAllByText('Solved ✓');
      expect(solvedBadges.length).toBeGreaterThanOrEqual(2);
    });
  });
});