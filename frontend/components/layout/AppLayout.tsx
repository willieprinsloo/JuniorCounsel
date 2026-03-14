'use client';

/**
 * Main Application Layout
 *
 * Wraps authenticated pages with Header and Sidebar.
 */

import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useAuth } from '@/lib/auth/context';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="h-screen bg-background transition-colors flex flex-col overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 p-6 overflow-hidden">
          <div className="mx-auto h-full" style={{ maxWidth: '1700px' }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
