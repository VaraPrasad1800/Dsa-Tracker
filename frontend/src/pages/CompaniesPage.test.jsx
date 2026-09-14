import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import CompaniesPage from './CompaniesPage';
import { problemsApi } from '../api/client';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../api/client', () => ({
  problemsApi: {
    getCompanies: vi.fn(),
  },
}));

describe('CompaniesPage', () => {
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
          <CompaniesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders company cards and pagination info from paginated backend response', async () => {
    problemsApi.getCompanies.mockResolvedValueOnce({
      data: {
        count: 55,
        next: 'http://example.com/api/problems/companies/?page=2',
        previous: null,
        results: [
          { id: 1, name: 'Google', slug: 'google', problem_count: 120, user_progress: { solved: 30 } },
          { id: 2, name: 'Meta', slug: 'meta', problem_count: 85, user_progress: { solved: 15 } },
        ],
      },
    });

    renderComponent();

    expect(await screen.findByText('Google')).toBeInTheDocument();
    expect(screen.getByText('Meta')).toBeInTheDocument();
    expect(screen.getByText(/55 tech giants/i)).toBeInTheDocument();
    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('navigates to /companies/:companySlug when a company card is clicked', async () => {
    problemsApi.getCompanies.mockResolvedValueOnce({
      data: {
        count: 1,
        results: [
          { id: 1, name: 'Amazon', slug: 'amazon', problem_count: 90, user_progress: { solved: 10 } },
        ],
      },
    });

    renderComponent();

    const companyCard = await screen.findByText('Amazon');
    fireEvent.click(companyCard);

    expect(mockNavigate).toHaveBeenCalledWith('/companies/amazon');
  });

  it('handles empty company list', async () => {
    problemsApi.getCompanies.mockResolvedValueOnce({
      data: { count: 0, results: [] },
    });

    renderComponent();

    expect(await screen.findByText('No companies tracked yet')).toBeInTheDocument();
  });
});
