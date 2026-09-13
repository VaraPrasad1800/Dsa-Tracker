import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import JudgePage from './JudgePage';
import { problemsApi, judgeApi } from '../api/client';

// Mock Monaco Editor for JSDOM
vi.mock('../components/judge/CodeEditor', () => ({
  default: ({ value, onChange }) => (
    <textarea
      data-testid="code-editor"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

const mockProblem = {
  id: 1,
  title: 'Two Sum',
  question_number: 1,
  difficulty: 'Easy',
  source_platform: 'LeetCode',
  is_judge_ready: true,
  description: 'Given an array of integers...',
};

const renderWithQueryClient = (ui) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('Judge Execution Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(problemsApi, 'getProblems').mockResolvedValue({
      data: { results: [mockProblem] },
    });
    vi.spyOn(problemsApi, 'getProblem').mockResolvedValue({
      data: mockProblem,
    });
    vi.spyOn(judgeApi, 'getTemplate').mockResolvedValue({
      data: { starter_code: 'def solve(): pass' },
    });
    vi.spyOn(judgeApi, 'getTestCases').mockResolvedValue({
      data: { test_cases: [{ id: 1, input_text: '2 7 11 15\n9', output_text: '[0, 1]' }] },
    });
    vi.spyOn(judgeApi, 'getSubmissions').mockResolvedValue({
      data: [],
    });
  });

  it('submitting code triggers pending state, polls status, and displays ACCEPTED verdict banner', async () => {
    vi.spyOn(judgeApi, 'submitCode').mockResolvedValueOnce({
      data: {
        submission_id: 'sub-async-123',
        verdict: 'PENDING',
      },
    });

    vi.spyOn(judgeApi, 'getSubmissionStatus').mockResolvedValueOnce({
      data: {
        submission_id: 'sub-async-123',
        verdict: 'ACCEPTED',
      },
    });

    vi.spyOn(judgeApi, 'getSubmissionDetail').mockResolvedValueOnce({
      data: {
        id: 'sub-async-123',
        verdict: 'ACCEPTED',
        tests_passed: 5,
        tests_total: 5,
        execution_time_ms: 38,
        memory_kb: 12400,
      },
    });

    renderWithQueryClient(<JudgePage initialProblemId={1} />);

    // Wait for the problem editor to populate
    const editor = await screen.findByTestId('code-editor');
    await waitFor(() => {
      expect(editor.value).toBeTruthy();
    });

    // Find and click the Submit button
    const submitBtn = screen.getByRole('button', { name: /Submit/i });
    expect(submitBtn).toBeInTheDocument();

    await act(async () => {
      submitBtn.click();
    });

    // Submitting code triggers pending state
    expect(judgeApi.submitCode).toHaveBeenCalledWith(
      expect.objectContaining({
        problem_id: 1,
        language: 'python',
      })
    );

    // After polling resolves and detail loads, verdict banner shows ACCEPTED
    await waitFor(() => {
      expect(screen.getByText('ACCEPTED')).toBeInTheDocument();
      expect(screen.getByText('(5/5 passed)')).toBeInTheDocument();
      expect(screen.getByText(/38 ms/)).toBeInTheDocument();
    });
  });

  it('displays WRONG_ANSWER verdict banner when submission fails test cases', async () => {
    vi.spyOn(judgeApi, 'submitCode').mockResolvedValueOnce({
      data: {
        submission_id: 'sub-async-456',
        verdict: 'PENDING',
      },
    });

    vi.spyOn(judgeApi, 'getSubmissionStatus').mockResolvedValueOnce({
      data: {
        submission_id: 'sub-async-456',
        verdict: 'WRONG_ANSWER',
      },
    });

    vi.spyOn(judgeApi, 'getSubmissionDetail').mockResolvedValueOnce({
      data: {
        id: 'sub-async-456',
        verdict: 'WRONG_ANSWER',
        tests_passed: 2,
        tests_total: 5,
        execution_time_ms: 42,
        memory_kb: 11200,
      },
    });

    renderWithQueryClient(<JudgePage initialProblemId={1} />);

    const editor = await screen.findByTestId('code-editor');
    await waitFor(() => {
      expect(editor.value).toBeTruthy();
    });

    const submitBtn = screen.getByRole('button', { name: /Submit/i });
    await act(async () => {
      submitBtn.click();
    });

    await waitFor(() => {
      expect(screen.getByText('WRONG_ANSWER')).toBeInTheDocument();
      expect(screen.getByText('(2/5 passed)')).toBeInTheDocument();
    });
  });
});
