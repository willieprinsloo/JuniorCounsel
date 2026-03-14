'use client';

/**
 * Auth Reset Page
 *
 * Clears authentication state and redirects to login.
 * Use this page if you're stuck in an auth loop.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ResetAuthPage() {
  const router = useRouter();

  useEffect(() => {
    // Clear all auth-related localStorage items
    localStorage.removeItem('authToken');

    // Optional: clear all localStorage if needed
    // localStorage.clear();

    // Redirect to login after a brief delay
    setTimeout(() => {
      router.push('/login');
    }, 1000);
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="text-center space-y-4">
        <div className="text-2xl font-semibold text-foreground">Clearing authentication...</div>
        <div className="text-muted-foreground">You will be redirected to login shortly.</div>
      </div>
    </div>
  );
}
