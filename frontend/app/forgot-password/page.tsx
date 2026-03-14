'use client';

import { useState } from 'react';
import Link from 'next/link';
import { authAPI } from '@/lib/api/services';
import { APIError } from '@/lib/api/client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await authAPI.forgotPassword({ email });
      setIsSubmitted(true);
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

  if (isSubmitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
          {/* Success icon */}
          <div className="flex justify-center mb-6">
            <div className="bg-green-100 rounded-full p-3">
              <svg className="w-12 h-12 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
            Check Your Email
          </h1>

          <p className="text-center text-gray-600 mb-6">
            If an account exists for <strong className="text-gray-900">{email}</strong>, you will receive a password reset link shortly.
          </p>

          <p className="text-sm text-center text-gray-500 mb-6">
            The link will expire in 1 hour.
          </p>

          <Link
            href="/login"
            className="block w-full bg-slate-800 text-white py-3 px-4 rounded-lg hover:bg-slate-700 transition-colors text-center font-semibold"
          >
            Return to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4 py-12">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Forgot Password?
          </h1>
          <p className="text-gray-600">
            Enter your email address and we'll send you a link to reset your password
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
              <span className="block sm:inline text-sm">{error}</span>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-gray-900 placeholder:text-gray-400 text-sm"
              placeholder="your.email@example.com"
              required
              autoComplete="email"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-slate-800 text-white py-3 px-4 rounded-lg hover:bg-slate-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-sm"
          >
            {isLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        {/* Back to login link */}
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
