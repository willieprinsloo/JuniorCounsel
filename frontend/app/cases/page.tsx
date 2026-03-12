'use client';

/**
 * Cases List Page
 *
 * Browse and manage all cases.
 */

import { useState, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { casesAPI } from '@/lib/api/services';
import { useAuth } from '@/lib/auth/context';
import type { Case } from '@/types/api';
import Link from 'next/link';

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { user } = useAuth();

  useEffect(() => {
    const loadCases = async () => {
      if (!user) return;

      try {
        setLoading(true);
        // TODO: Get organisation_id from user context
        // For now, using placeholder
        const response = await casesAPI.list({
          organisation_id: 1,
          page,
          per_page: 20,
        });

        setCases(response.data);
        setTotal(response.total);
      } catch (err) {
        setError('Failed to load cases');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadCases();
  }, [page, user]);

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Cases</h1>
          <Link
            href="/cases/new"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            Create New Case
          </Link>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading cases...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {!loading && !error && cases.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No cases found.</p>
            <Link
              href="/cases/new"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200"
            >
              Create your first case
            </Link>
          </div>
        )}

        {!loading && !error && cases.length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {cases.map((caseItem) => (
                <li key={caseItem.id}>
                  <Link
                    href={`/cases/${caseItem.id}`}
                    className="block hover:bg-gray-50 transition-colors"
                  >
                    <div className="px-4 py-4 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-blue-600 truncate">
                            {caseItem.title}
                          </p>
                          {caseItem.description && (
                            <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                              {caseItem.description}
                            </p>
                          )}
                        </div>
                        <div className="ml-4 flex-shrink-0">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              caseItem.status === 'active'
                                ? 'bg-green-100 text-green-800'
                                : caseItem.status === 'closed'
                                ? 'bg-gray-100 text-gray-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {caseItem.status}
                          </span>
                        </div>
                      </div>
                      <div className="mt-2 sm:flex sm:justify-between">
                        <div className="sm:flex space-x-4">
                          {caseItem.case_type && (
                            <p className="flex items-center text-sm text-gray-500">
                              Type: {caseItem.case_type}
                            </p>
                          )}
                          {caseItem.jurisdiction && (
                            <p className="flex items-center text-sm text-gray-500">
                              Jurisdiction: {caseItem.jurisdiction}
                            </p>
                          )}
                        </div>
                        <div className="mt-2 sm:mt-0">
                          <p className="text-sm text-gray-500">
                            Created {new Date(caseItem.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!loading && !error && total > 20 && (
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-lg shadow">
            <div className="flex flex-1 justify-between sm:hidden">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page * 20 >= total}
                className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing page <span className="font-medium">{page}</span> of{' '}
                  <span className="font-medium">{Math.ceil(total / 20)}</span>
                </p>
              </div>
              <div>
                <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page * 20 >= total}
                    className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
