import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ProblemsPage from './ProblemsPage';
import { problemsApi, progressApi } from '../api/client';

import { TagProvider } from '../context/TagContext';

vi.mock('../components/dashboard/HeroOrb', () => ({
  default: () => <div data-testid="hero-orb">HeroOrb</div>,
}));

vi.mock('../api/client', () => ({
  problemsApi: {
    getProblems: vi.fn(),
    getProblem: vi.fn(),
    getTags: vi.fn().mockResolvedValue({ data: [] }),
    getCompanies: vi.fn().mockResolvedValue({ data: [] }),
    getTopicPractice: vi.fn(),
  },
  progressApi: {
    getStats: vi.fn().mockResolvedValue({ data: {} }),
    saveProgress: vi.fn(),
  },
}));

describe('ProblemsPage Error & Success States', () => {
  let queryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TagProvider>
            <ProblemsPage />
          </TagProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders visible error state with retry button when backend fails', async () => {
    problemsApi.getProblems.mockRejectedValue(new Error('Network Error: Connection refused'));

    renderComponent();

    expect(await screen.findByText('Failed to Load Problems')).toBeInTheDocument();
    expect(screen.getByText(/Network Error: Connection refused/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Retry Loading/i })).toBeInTheDocument();
  });

  it('renders problem list successfully when API resolves', async () => {
    problemsApi.getProblems.mockResolvedValueOnce({
      data: {
        count: 1,
        results: [
          {
            id: '1',
            question_number: 1,
            title: 'Two Sum',
            slug: 'two-sum',
            difficulty: 'Easy',
            tags: [{ id: 1, name: 'Array', slug: 'array' }],
            companies: [],
            frequency: 100,
            is_premium: false,
          },
        ],
        counts: { total: 1, easy: 1, medium: 0, hard: 0 },
      },
    });

    renderComponent();

    expect(await screen.findByText('Two Sum')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
  });
});
