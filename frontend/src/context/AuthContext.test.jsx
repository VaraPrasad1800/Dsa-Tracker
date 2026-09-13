import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import { AuthProvider, useAuth } from './AuthContext';
import api, {
  authApi,
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  USER_KEY,
} from '../api/client';

// Test consumer component
const ConsumerComponent = () => {
  const { user, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="username">{user?.username || 'none'}</div>
      <button onClick={() => login({ username: 'testuser', password: 'password123' })}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

const renderWithProviders = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ConsumerComponent />
      </AuthProvider>
    </QueryClientProvider>
  );
};

describe('AuthContext Flow', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('initializes in unauthenticated state when localStorage is empty', () => {
    renderWithProviders();
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
    expect(screen.getByTestId('username').textContent).toBe('none');
  });

  it('login sets tokens in localStorage and updates user state', async () => {
    const mockUser = { id: 1, username: 'testuser', email: 'test@example.com' };
    vi.spyOn(authApi, 'login').mockResolvedValueOnce({
      data: {
        access_token: 'fake-access-token',
        refresh_token: 'fake-refresh-token',
        user: mockUser,
      },
    });
    vi.spyOn(authApi, 'getMe').mockResolvedValueOnce({
      data: mockUser,
    });

    renderWithProviders();

    await act(async () => {
      screen.getByText('Login').click();
    });

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe('fake-access-token');
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('fake-refresh-token');
    expect(JSON.parse(localStorage.getItem(USER_KEY))).toEqual(mockUser);

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');
    expect(screen.getByTestId('username').textContent).toBe('testuser');
  });

  it('logout clears tokens from localStorage and resets user state', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'existing-access');
    localStorage.setItem(REFRESH_TOKEN_KEY, 'existing-refresh');
    localStorage.setItem(USER_KEY, JSON.stringify({ id: 1, username: 'existinguser' }));

    vi.spyOn(authApi, 'logout').mockResolvedValueOnce({ data: { message: 'Logged out' } });

    renderWithProviders();
    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');

    await act(async () => {
      screen.getByText('Logout').click();
    });

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(USER_KEY)).toBeNull();
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
  });

  it('transparently retries requests after token refresh on 401', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'expired-access');
    localStorage.setItem(REFRESH_TOKEN_KEY, 'valid-refresh');

    const fakeRefreshPost = vi.fn().mockResolvedValue({
      data: {
        access_token: 'new-fresh-access-token',
        refresh_token: 'new-fresh-refresh-token',
      },
    });
    vi.spyOn(axios, 'create').mockImplementation(() => ({
      post: fakeRefreshPost,
    }));

    const mockAdapter = vi.fn()
      .mockRejectedValueOnce({
        config: { headers: {} },
        response: { status: 401, data: { detail: 'Token expired' } },
      })
      .mockResolvedValueOnce({
        status: 200,
        data: { success: true },
      });

    const originalAdapter = api.defaults.adapter;
    api.defaults.adapter = mockAdapter;

    try {
      const res = await api.get('/test-endpoint/');
      expect(fakeRefreshPost).toHaveBeenCalledWith('/auth/refresh-token/', {
        refresh_token: 'valid-refresh',
      });
      expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe('new-fresh-access-token');
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('new-fresh-refresh-token');
      expect(res.data).toEqual({ success: true });
    } finally {
      api.defaults.adapter = originalAdapter;
    }
  });
});
