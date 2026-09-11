import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../utils/errors';
import AuthLayout from './AuthLayout';
import { Field, SubmitButton, ErrorBanner, SuccessBanner } from './AuthFields';

export default function ForgotPasswordPage() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      const res = await forgotPassword(email);
      // Backend always returns the same message to avoid email enumeration.
      setSuccess(
        res.message ||
        'If an account with that email exists, a password reset link has been sent.'
      );
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout subtitle="We'll send you a reset link">
      <h2 className="text-xl font-bold text-white mb-1">Forgot Password</h2>
      <p className="text-sm text-slate-400 mb-6">
        Enter the email linked to your account and we'll email you a reset link.
      </p>

      <ErrorBanner message={error} />
      <SuccessBanner message={success} />

      {!success && (
        <form onSubmit={handleSubmit} className="space-y-4">
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
          <SubmitButton disabled={submitting}>{submitting ? 'Sending link…' : 'Send Reset Link'}</SubmitButton>
        </form>
      )}

      <div className="mt-6 text-center text-sm text-slate-400">
        Remembered it?{' '}
        <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
}