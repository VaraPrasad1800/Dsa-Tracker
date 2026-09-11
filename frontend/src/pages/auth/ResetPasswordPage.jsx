import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../utils/errors';
import AuthLayout from './AuthLayout';
import { Field, SubmitButton, ErrorBanner, SuccessBanner } from './AuthFields';

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (!token) {
      setError('Invalid or missing reset token. Please use the link from your email.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await resetPassword(token, newPassword);
      setSuccess(
        res.message ||
        'Password reset successful. You can now log in with your new password.'
      );
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout subtitle="Set a new password">
      <h2 className="text-xl font-bold text-white mb-1">Reset Password</h2>
      <p className="text-sm text-slate-400 mb-6">Choose a strong, new password for your account.</p>

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
            label="New Password"
            id="newPassword"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Min 8 characters"
            required
            autoComplete="new-password"
            hint="At least 8 characters, can't be entirely numeric."
          />
          <Field
            label="Confirm Password"
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter new password"
            required
            autoComplete="new-password"
          />
          <SubmitButton disabled={submitting}>{submitting ? 'Resetting…' : 'Reset Password'}</SubmitButton>
        </form>
      )}

      <div className="mt-6 text-center text-sm text-slate-400">
        <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
}