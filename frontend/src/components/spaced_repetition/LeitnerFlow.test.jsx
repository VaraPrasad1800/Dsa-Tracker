import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ReviewProblemCard from './ReviewProblemCard';
import LeitnerBoxGrid from './LeitnerBoxGrid';
import TodaysReviewPage from '../../pages/TodaysReviewPage';
import { spacedRepetitionApi, progressApi } from '../../api/client';

const mockItemBox1 = {
  id: 1,
  current_box: 1,
  times_solved: 0,
  times_attempted: 1,
  problem: {
    id: 101,
    title: 'Two Sum',
    question_number: 1,
    difficulty: 'Easy',
    source_platform: 'LeetCode',
    source_url: 'https://leetcode.com/problems/two-sum/',
    tags: [{ id: 1, name: 'Array' }],
    companies: [{ id: 1, name: 'Google' }],
  },
};

const mockItemBox3 = {
  id: 2,
  current_box: 3,
  times_solved: 2,
  times_attempted: 3,
  problem: {
    id: 102,
    title: '3Sum',
    question_number: 15,
    difficulty: 'Medium',
    source_platform: 'LeetCode',
    tags: [{ id: 1, name: 'Array' }],
    companies: [{ id: 2, name: 'Amazon' }],
  },
};

const renderWithQueryClient = (ui) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('Leitner System Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders problem card displaying current Box 1 and triggers SOLVED action', () => {
    const handleAction = vi.fn();
    render(<ReviewProblemCard item={mockItemBox1} onAction={handleAction} />);

    expect(screen.getByText('Currently in Box 1')).toBeInTheDocument();
    expect(screen.getByText('Two Sum')).toBeInTheDocument();

    const solvedBtn = screen.getByRole('button', { name: /Solved/i });
    solvedBtn.click();

    expect(handleAction).toHaveBeenCalledWith(101, 'SOLVED');
  });

  it('triggers NEEDS_REVISIT action to reset to Box 1', () => {
    const handleAction = vi.fn();
    render(<ReviewProblemCard item={mockItemBox3} onAction={handleAction} />);

    expect(screen.getByText('Currently in Box 3')).toBeInTheDocument();
    expect(screen.getByText('3Sum')).toBeInTheDocument();

    const revisitBtn = screen.getByRole('button', { name: /Needs Revisit/i });
    revisitBtn.click();

    expect(handleAction).toHaveBeenCalledWith(102, 'NEEDS_REVISIT');
  });

  it('TodaysReviewPage advances box on solve mutation', async () => {
    vi.spyOn(spacedRepetitionApi, 'getDueToday').mockResolvedValueOnce({
      data: [mockItemBox1],
    });
    vi.spyOn(spacedRepetitionApi, 'getStats').mockResolvedValueOnce({
      data: { box_1_count: 1, box_2_count: 0, box_3_count: 0, box_4_count: 0, box_5_count: 0 },
    });
    const saveProgressSpy = vi.spyOn(progressApi, 'saveProgress').mockResolvedValueOnce({
      data: { success: true, new_box: 2 },
    });

    renderWithQueryClient(<TodaysReviewPage />);

    // Wait for due item to load
    const title = await screen.findByText('Two Sum');
    expect(title).toBeInTheDocument();
    expect(screen.getByText('Currently in Box 1')).toBeInTheDocument();

    const solvedBtn = screen.getByRole('button', { name: /Solved/i });
    await act(async () => {
      solvedBtn.click();
    });

    expect(saveProgressSpy).toHaveBeenCalledWith({
      problem_id: 101,
      status: 'SOLVED',
    });
  });

  it('TodaysReviewPage resets to Box 1 on revisit mutation', async () => {
    vi.spyOn(spacedRepetitionApi, 'getDueToday').mockResolvedValueOnce({
      data: [mockItemBox3],
    });
    vi.spyOn(spacedRepetitionApi, 'getStats').mockResolvedValueOnce({
      data: { box_1_count: 0, box_2_count: 0, box_3_count: 1, box_4_count: 0, box_5_count: 0 },
    });
    const saveProgressSpy = vi.spyOn(progressApi, 'saveProgress').mockResolvedValueOnce({
      data: { success: true, new_box: 1 },
    });

    renderWithQueryClient(<TodaysReviewPage />);

    const title = await screen.findByText('3Sum');
    expect(title).toBeInTheDocument();
    expect(screen.getByText('Currently in Box 3')).toBeInTheDocument();

    const revisitBtn = screen.getByRole('button', { name: /Needs Revisit/i });
    await act(async () => {
      revisitBtn.click();
    });

    expect(saveProgressSpy).toHaveBeenCalledWith({
      problem_id: 102,
      status: 'NEEDS_REVISIT',
    });
  });

  it('LeitnerBoxGrid accurately displays counts across boxes 1 to 5', () => {
    const stats = {
      box_1_count: 5,
      box_2_count: 3,
      box_3_count: 8,
      box_4_count: 2,
      box_5_count: 12,
    };
    render(<LeitnerBoxGrid stats={stats} />);

    expect(screen.getByText('Active Memory Cards:')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument(); // 5+3+8+2+12
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });
});
