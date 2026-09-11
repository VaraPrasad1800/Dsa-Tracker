import React, { useState } from 'react';
import { Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { extractError, extractErrorCode } from '../../utils/errors';
import AuthLayout from './AuthLayout';
import { Field, SubmitButton, ErrorBanner } from './AuthFields';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [unverifiedEmail, setUnverifiedEmail] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || '/';

  // If already logged in, go straight to the app.
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setUnverifiedEmail(null);
    setSubmitting(true);
    try {
      await login({ username: identifier, password });
      navigate(from, { replace: true });
    } catch (err) {
      if (extractErrorCode(err) === 'email_not_verified') {
        setUnverifiedEmail(err.response?.data?.email || null);
        setError(extractError(err));
      } else {
        setError(extractError(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout subtitle="Sign in to continue your preparation">
      <h2 className="text-xl font-bold text-white mb-1">Welcome back</h2>
      <p className="text-sm text-slate-400 mb-6">Log in to access your problem bank, review queue and analytics.</p>

      <ErrorBanner message={error} />

      {unverifiedEmail && (
        <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span>Verify your email to enable login.</span>
            <Link
              to="/verify-email"
              state={{ email: unverifiedEmail }}
              className="shrink-0 font-medium text-amber-300 hover:text-amber-200 underline"
            >
              Verify now
            </Link>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Username or Email"
          id="identifier"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder="Enter username or email"
          required
          autoComplete="username"
        />
        <Field
          label="Password"
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
          required
          autoComplete="current-password"
        />
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm text-indigo-400 hover:text-indigo-300">
            Forgot password?
          </Link>
        </div>
        <SubmitButton disabled={submitting}>{submitting ? 'Signing in…' : 'Sign In'}</SubmitButton>
      </form>

      <div className="mt-6 text-center text-sm text-slate-400">
        Don't have an account?{' '}
        <Link to="/signup" className="font-medium text-indigo-400 hover:text-indigo-300">
          Sign up
        </Link>
      </div>
    </AuthLayout>
  );
}