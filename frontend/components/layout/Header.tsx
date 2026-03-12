'use client';

/**
 * Application Header
 *
 * Top navigation bar with user menu and logout.
 */

import { useAuth } from '@/lib/auth/context';

export function Header() {
  const { user, logout, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="flex items-center justify-between h-16 px-6">
        <div className="flex items-center">
          <h1 className="text-xl font-semibold text-gray-900">Junior Counsel</h1>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-700">
            {user?.full_name || user?.email}
          </div>

          <button
            onClick={logout}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
