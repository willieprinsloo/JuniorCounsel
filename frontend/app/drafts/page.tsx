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
      initializing: 'bg-blue-100 text-blue-800',
      awaiting_intake: 'bg-purple-100 text-purple-800',
      research: 'bg-yellow-100 text-yellow-800',
      drafting: 'bg-yellow-100 text-yellow-800',
      review: 'bg-orange-100 text-orange-800',
      ready: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">All Drafts</h1>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading drafts...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {!loading && !error && drafts.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No drafts found.</p>
            <Link
              href="/cases"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200"
            >
              Go to Cases
            </Link>
          </div>
        )}

        {!loading && !error && drafts.length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {drafts.map((draft) => (
                <li key={draft.id}>
                  <Link
                    href={`/drafts/${draft.id}`}
                    className="block px-4 py-4 sm:px-6 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-blue-600 truncate">
                          {draft.title}
                        </p>
                        <div className="mt-1 flex items-center space-x-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(draft.status)}`}>
                            {draft.status.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-gray-500">
                            {draft.document_type}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4 flex-shrink-0 text-xs text-gray-500">
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
