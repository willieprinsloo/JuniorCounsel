'use client';

/**
 * Login Page
 *
 * User authentication interface with brand identity.
 */

import { useState, useEffect, Suspense } from 'react';
import { useAuth } from '@/lib/auth/context';
import { useRouter, useSearchParams } from 'next/navigation';
import { APIError } from '@/lib/api/client';
import Image from 'next/image';

function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);

  const { login, isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const isDev = process.env.NODE_ENV === 'development';

  // Check for session expiration and redirect parameters
  useEffect(() => {
    const expired = searchParams.get('expired');
    if (expired === 'true') {
      setSessionExpired(true);
      setError('Your session has expired. Please log in again.');
    }
  }, [searchParams]);

  useEffect(() => {
    if (isAuthenticated) {
      // Redirect to original page if provided, otherwise go to cases
      const redirectTo = searchParams.get('redirect');
      router.push(redirectTo || '/cases');
    }
  }, [isAuthenticated, router, searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSessionExpired(false); // Clear session expired flag on new login attempt
    setIsLoading(true);

    try {
      await login({ username, password });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#fcfbf8]">
      {/* Left Column - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 lg:p-12">
        <div className="max-w-md w-full space-y-8">
          {/* Brand Header */}
          <div className="text-center">
            <div className="flex justify-center mb-8">
              <Image
                src="/logo-no-text.svg"
                alt="Junior Counsel Logo"
                width={120}
                height={120}
                className="w-24 h-24 sm:w-28 sm:h-28 object-contain"
                priority
              />
            </div>
          </div>

          {/* Login Form Card */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-5">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  id="username"
                  name="username"
                  type="email"
                  required
                  autoComplete="email"
                  className="block w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-sm transition-all"
                  placeholder="your.email@example.com"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Password
                  </label>
                  <a
                    href="/forgot-password"
                    className="text-sm text-slate-800 hover:text-slate-600 font-medium"
                  >
                    Forgot password?
                  </a>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  className="block w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-slate-800 focus:border-transparent text-sm transition-all"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            {error && (
              <div className={`rounded-lg p-4 ${sessionExpired ? 'bg-amber-50 border border-amber-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center">
                  {sessionExpired ? (
                    <svg className="w-5 h-5 text-amber-600 mr-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-red-600 mr-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                    </svg>
                  )}
                  <p className={`text-sm font-medium ${sessionExpired ? 'text-amber-800' : 'text-red-800'}`}>{error}</p>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-slate-800 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Test Credentials (Development Only) */}
        {isDev && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">Development Mode - Test Credentials</h3>
                <div className="space-y-3">
                  <div className="bg-white rounded-md px-3 py-2 border border-blue-100">
                    <p className="text-xs font-semibold text-gray-700 mb-1">Admin User</p>
                    <p className="text-xs text-gray-600 font-mono">willie@lawfirm.co.za</p>
                    <p className="text-xs text-gray-600 font-mono">password123</p>
                  </div>
                  <div className="bg-white rounded-md px-3 py-2 border border-blue-100">
                    <p className="text-xs font-semibold text-gray-700 mb-1">Regular User</p>
                    <p className="text-xs text-gray-600 font-mono">advocate@chambers.co.za</p>
                    <p className="text-xs text-gray-600 font-mono">password123</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

          {/* Footer */}
          <p className="text-center text-xs text-gray-500">
            &copy; 2025 Junior Counsel. All rights reserved.
          </p>
        </div>
      </div>

      {/* Right Column - Imagery (hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-800 items-center justify-center p-12 relative overflow-hidden">
        <div className="relative z-10 text-white max-w-lg">
          <h2 className="text-4xl font-bold mb-6">
            AI-Powered Legal Document Processing
          </h2>
          <p className="text-lg text-gray-300 mb-8">
            Draft court-ready documents with confidence. Junior Counsel assists South African legal professionals with intelligent document analysis and citation support.
          </p>

          {/* Document Preview Illustration */}
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-semibold">Automated Document Analysis</p>
                  <p className="text-sm text-gray-400">Extract key information from pleadings, evidence, and correspondence</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-semibold">Court-Ready Drafts</p>
                  <p className="text-sm text-gray-400">Generate affidavits, heads of argument, and pleadings with proper citations</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-semibold">South African Litigation Focus</p>
                  <p className="text-sm text-gray-400">Built specifically for SA legal practice and court requirements</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-64 h-64 bg-white rounded-full filter blur-3xl"></div>
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-white rounded-full filter blur-3xl"></div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#fcfbf8]">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800"></div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
