import React, { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { extractError, extractErrorCode } from '../../utils/errors';
import AuthLayout from './AuthLayout';
import { Field, SubmitButton, ErrorBanner, SuccessBanner } from './AuthFields';

export default function VerifyEmailPage() {
  const { verifyEmail, resendVerification } = useAuth();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const token = (searchParams.get('token') || '').trim();
  const [email, setEmail] = useState(location.state?.email || '');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const hasRequestedRef = useRef(false);

  // Auto-verify on load when a token is present (from the email link).
  useEffect(() => {
    if (token && !hasRequestedRef.current) {
      hasRequestedRef.current = true;
      const verify = async () => {
        setSubmitting(true);
        try {
          const res = await verifyEmail(token);
          setSuccess(res.message || 'Email verified successfully. You can now log in.');
        } catch (err) {
          const code = extractErrorCode(err);
          if (code === 'already_used') {
            setSuccess('Your email address is already verified! You can now log in.');
          } else {
            setError(extractError(err));
          }
        } finally {
          setSubmitting(false);
        }
      };
      verify();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleResend = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      const res = await resendVerification(email);
      setSuccess(
        res.message ||
        (res.verification_email_sent
          ? 'Verification email sent. Please check your inbox.'
          : 'If an account with that email exists, a verification email has been sent.')
      );
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout subtitle="Verify your email address">
      {token ? (
        <>
          <h2 className="text-xl font-bold text-white mb-1">Verifying your email…</h2>
          <p className="text-sm text-slate-400 mb-6">
            {submitting ? 'Please wait a moment.' : 'Processing your verification link.'}
          </p>
          <ErrorBanner message={error} />
          <SuccessBanner message={success} />
          {success && (
            <div className="mt-4 text-sm text-slate-300">
              <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
                Go to Sign In →
              </Link>
            </div>
          )}
          {error && !success && (
            <form onSubmit={handleResend} className="mt-6 space-y-4">
              <p className="text-sm text-slate-400">
                Request a new verification link below, then check your inbox.
              </p>
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
              <SubmitButton disabled={submitting}>Resend Verification Email</SubmitButton>
            </form>
          )}
        </>
      ) : (
        <>
          <h2 className="text-xl font-bold text-white mb-1">Didn't get your link?</h2>
          <p className="text-sm text-slate-400 mb-6">
            Enter your email to receive a new verification link.
          </p>
          <ErrorBanner message={error} />
          <SuccessBanner message={success} />
          {!success && (
            <form onSubmit={handleResend} className="space-y-4">
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
              <SubmitButton disabled={submitting}>{submitting ? 'Sending…' : 'Send Verification Email'}</SubmitButton>
            </form>
          )}
        </>
      )}

      <div className="mt-6 text-center text-sm text-slate-400">
        <Link to="/login" className="font-medium text-indigo-400 hover:text-indigo-300">
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
}