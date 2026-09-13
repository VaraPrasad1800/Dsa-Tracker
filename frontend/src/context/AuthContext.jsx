import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  authApi,
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  USER_KEY,
  getAccessToken,
  getRefreshToken,
} from '../api/client';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const queryClient = useQueryClient();

  const isAuthenticated = !!user && !!getAccessToken();

  const storeTokens = (access, refresh) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  };

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  // Load user on mount (if a token exists)
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const token = getAccessToken();
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await authApi.getMe();
        if (!cancelled) {
          setUser(res.data);
          localStorage.setItem(USER_KEY, JSON.stringify(res.data));
        }
      } catch (err) {
        if (!cancelled) {
          const status = err?.response?.status;
          // Only wipe the session on real auth failures (401/403).
          // On network or server errors keep tokens so the user can
          // retry without being silently logged out to a blank page.
          if (status === 401 || status === 403) {
            clearSession();
          } else {
            setAuthError('Could not verify your session. Please check your connection and reload.');
          }
        }
      } finally {
        setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [clearSession]);

  const login = async ({ username, password, email }) => {
    setAuthError(null);
    const body = email ? { email, password } : { username, password };
    const res = await authApi.login(body);
    storeTokens(res.data.access_token, res.data.refresh_token);
    try {
      const meRes = await authApi.getMe();
      setUser(meRes.data);
      localStorage.setItem(USER_KEY, JSON.stringify(meRes.data));
    } catch (err) {
      // Login succeeded but getMe failed — clean up stale tokens so
      // the user is not left in a half-authenticated state.
      clearSession();
      const message = err?.response?.data?.detail
        || err?.message
        || 'Login succeeded but we could not load your profile. Please try again.';
      setAuthError(message);
      throw new Error(message);
    }
    queryClient.invalidateQueries();
    return res.data;
  };

  const signup = async ({ username, email, password }) => {
    setAuthError(null);
    const res = await authApi.signup({ username, email, password });
    // Signup does not return tokens — user must verify email first.
    return res.data;
  };

  const verifyEmail = async (token) => {
    setAuthError(null);
    const res = await authApi.verifyEmail(token);
    return res.data;
  };

  const resendVerification = async (email) => {
    setAuthError(null);
    const res = await authApi.resendVerification(email);
    return res.data;
  };

  const forgotPassword = async (email) => {
    setAuthError(null);
    const res = await authApi.forgotPassword(email);
    return res.data;
  };

  const resetPassword = async (token, newPassword) => {
    setAuthError(null);
    const res = await authApi.resetPassword(token, newPassword);
    return res.data;
  };

  const logout = async () => {
    const refresh = getRefreshToken() || localStorage.getItem(REFRESH_TOKEN_KEY);
    if (refresh) {
      try {
        await authApi.logout(refresh);
      } catch {
        // Continue clearing local state even if revocation request fails
      }
    }
    clearSession();
    queryClient.clear();
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      loading,
      authError,
      setAuthError,
      login,
      signup,
      verifyEmail,
      resendVerification,
      forgotPassword,
      resetPassword,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);