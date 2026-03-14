'use client';

/**
 * Drafts List Page
 *
 * Browse all draft sessions across all cases.
 */

import { useState, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { draftSessionsAPI } from '@/lib/api/services';
import { useAuth } from '@/lib/auth/context';
import type { DraftSession } from '@/types/api';
import Link from 'next/link';

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<DraftSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();

  useEffect(() => {
    const loadDrafts = async () => {
      if (!user) return;

      try {
        setLoading(true);
        // Note: This would need to be updated to fetch across all cases
        // For now, this is a placeholder implementation
        setDrafts([]);
      } catch (err) {
        setError('Failed to load drafts');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadDrafts();
  }, [user]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      initializing: 'bg-secondary/10 text-secondary border border-secondary/20',
      awaiting_intake: 'bg-secondary/10 text-secondary border border-secondary/20',
      research: 'bg-secondary/10 text-secondary border border-secondary/20',
      drafting: 'bg-secondary/10 text-secondary border border-secondary/20',
      review: 'bg-secondary/10 text-secondary border border-secondary/20',
      ready: 'bg-success/10 text-success border border-success/20',
      failed: 'bg-destructive/10 text-destructive border border-destructive/20',
    };
    return colors[status] || 'bg-muted text-muted-foreground border border-border';
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">All Drafts</h1>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading drafts...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/30 p-4">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {!loading && !error && drafts.length === 0 && (
          <div className="text-center py-12 bg-card border border-border rounded-lg shadow-sm">
            <p className="text-muted-foreground">No drafts found.</p>
            <Link
              href="/cases"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
            >
              Go to Cases
            </Link>
          </div>
        )}

        {!loading && !error && drafts.length > 0 && (
          <div className="bg-card border border-border shadow-sm overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-border">
              {drafts.map((draft) => (
                <li key={draft.id}>
                  <Link
                    href={`/drafts/${draft.id}`}
                    className="block px-4 py-4 sm:px-6 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-primary truncate">
                          {draft.title}
                        </p>
                        <div className="mt-1 flex items-center space-x-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(draft.status)}`}>
                            {/* Show spinner for processing states */}
                            {(draft.status === 'research' || draft.status === 'drafting' || draft.status === 'initializing') && (
                              <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                            )}
                            {draft.status.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {draft.document_type}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4 flex-shrink-0 text-xs text-muted-foreground">
                        {new Date(draft.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
