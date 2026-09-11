import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../utils/errors';
import AuthLayout from './AuthLayout';
import { Field, SubmitButton, ErrorBanner, SuccessBanner } from './AuthFields';

export default function SignupPage() {
  const { signup } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      const res = await signup({ username, email, password });
      setSuccess(
        res.message ||
        'Account created! Check your email to verify your account before logging in.'
      );
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout subtitle="Create your free account">
      <h2 className="text-xl font-bold text-white mb-1">Create Account</h2>
      <p className="text-sm text-slate-400 mb-6">You'll receive a verification email before you can log in.</p>

      <ErrorBanner message={error} />
      <SuccessBanner message={success} />

      {success ? (
        <div className="mt-4 text-sm text-slate-300">
          <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
            Go to Sign In →
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field
            label="Username"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="At least 3 characters"
            required
            autoComplete="username"
          />
          <Field
            label="Email"
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoComplete="email"
          />
          <Field
            label="Password"
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 8 characters, not entirely numeric"
            required
            autoComplete="new-password"
            hint="At least 8 characters, can't be entirely numeric."
          />
          <SubmitButton disabled={submitting}>{submitting ? 'Creating account…' : 'Create Account'}</SubmitButton>
        </form>
      )}

      <div className="mt-6 text-center text-sm text-slate-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
}