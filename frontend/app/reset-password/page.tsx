'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api/services';
import { APIError } from '@/lib/api/client';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(true);
  const [isTokenValid, setIsTokenValid] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Verify token on mount
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setError('No reset token provided');
        setIsVerifying(false);
        return;
      }

      try {
        const response = await authAPI.verifyResetToken({ token });
        if (response.valid) {
          setIsTokenValid(true);
        } else {
          setError(response.message);
        }
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.message);
        } else {
          setError('Failed to verify reset token');
        }
      } finally {
        setIsVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!newPassword || !confirmPassword) {
      setError('Please enter and confirm your new password');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!token) {
      setError('No reset token provided');
      return;
    }

    setIsLoading(true);

    try {
      await authAPI.resetPassword({
        token,
        new_password: newPassword,
      });
      setIsSuccess(true);

      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state while verifying token
  if (isVerifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfbf8] p-4">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto mb-4"></div>
            <p className="text-gray-600">Verifying reset link...</p>
          </div>
        </div>
      </div>
    );
  }

  // Invalid token state
  if (!isTokenValid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfbf8] p-4">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
          <div className="flex justify-center mb-6">
            <div className="bg-red-100 rounded-full p-3">
              <svg className="w-12 h-12 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
            Invalid Reset Link
          </h1>

          <p className="text-center text-gray-600 mb-6">
            {error || 'This password reset link is invalid or has expired.'}
          </p>

          <div className="space-y-3">
            <Link
              href="/forgot-password"
              className="block w-full bg-slate-800 text-white py-3 px-4 rounded-lg hover:bg-slate-700 transition-colors text-center font-semibold"
            >
              Request New Reset Link
            </Link>
            <Link
              href="/login"
              className="block w-full border border-gray-300 bg-white py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors text-center font-semibold text-gray-900"
            >
              Return to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfbf8] p-4">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
          <div className="flex justify-center mb-6">
            <div className="bg-green-100 rounded-full p-3">
              <svg className="w-12 h-12 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
            Password Reset Successful
          </h1>

          <p className="text-center text-gray-600 mb-6">
            Your password has been successfully reset. You can now log in with your new password.
          </p>

          <p className="text-sm text-center text-gray-500 mb-6">
            Redirecting to login page...
          </p>

          <Link
            href="/login"
            className="block w-full bg-slate-800 text-white py-3 px-4 rounded-lg hover:bg-slate-700 transition-colors text-center font-semibold"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  // Reset password form
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fcfbf8] p-4 py-12">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Reset Password
          </h1>
          <p className="text-gray-600">
            Enter your new password below
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
              <span className="block sm:inline text-sm">{error}</span>
            </div>
          )}

          <div>
            <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-2">
              New Password
            </label>
            <input
              type="password"
              id="newPassword"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-gray-900 placeholder:text-gray-400 text-sm"
              placeholder="Enter new password"
              required
              disabled={isLoading}
              minLength={8}
            />
            <p className="mt-1 text-xs text-gray-500">
              Must be at least 8 characters long
            </p>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-gray-900 placeholder:text-gray-400 text-sm"
              placeholder="Confirm new password"
              required
              disabled={isLoading}
              minLength={8}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-slate-800 text-white py-3 px-4 rounded-lg hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-sm"
          >
            {isLoading ? 'Resetting Password...' : 'Reset Password'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link
            href="/login"
            className="text-sm text-slate-800 hover:text-slate-600 font-medium"
          >
            ← Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="bg-card border border-border rounded-lg shadow-lg p-8 w-full max-w-md">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </div>
      </div>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}
