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
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { Case } from '@/types/api';
import Link from 'next/link';

// Helper function to format text (remove underscores, capitalize)
function formatText(text: string | null | undefined): string {
  if (!text) return '';
  return text.replace(/_/g, ' ');
}

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [caseToDelete, setCaseToDelete] = useState<Case | null>(null);
  const [deleting, setDeleting] = useState(false);
  const { user} = useAuth();

  useEffect(() => {
    const loadCases = async () => {
      if (!user || !user.organisation_id) {
        setLoading(false);
        setError('You must be part of an organisation to view cases');
        return;
      }

      try {
        setLoading(true);
        setError(''); // Clear any previous errors

        const response = await casesAPI.list({
          organisation_id: user.organisation_id, // Now using actual organisation_id from user!
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

  const handleDeleteClick = (caseItem: Case, e: React.MouseEvent) => {
    e.preventDefault(); // Prevent link navigation
    e.stopPropagation();
    setCaseToDelete(caseItem);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!caseToDelete) return;

    try {
      setDeleting(true);
      await casesAPI.delete(caseToDelete.id);

      // Remove from local state
      setCases(cases.filter((c) => c.id !== caseToDelete.id));
      setTotal(total - 1);

      setDeleteDialogOpen(false);
      setCaseToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete case');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setCaseToDelete(null);
  };

  return (
    <AppLayout>
      <div className="h-full overflow-y-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">Cases</h1>
          <Link
            href="/cases/new"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
          >
            Create New Case
          </Link>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading cases...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/30 p-4">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {!loading && !error && cases.length === 0 && (
          <div className="text-center py-12 bg-card border border-border rounded-lg shadow-sm">
            <p className="text-muted-foreground">No cases found.</p>
            <Link
              href="/cases/new"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
            >
              Create your first case
            </Link>
          </div>
        )}

        {!loading && !error && cases.length > 0 && (
          <div className="bg-card border border-border shadow-sm overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-border">
              {cases.map((caseItem) => (
                <li key={caseItem.id}>
                  <div className="flex items-stretch hover:bg-accent/50 transition-colors">
                    <Link
                      href={`/cases/${caseItem.id}`}
                      className="flex-1 block"
                    >
                      <div className="px-4 py-4 sm:px-6">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-primary truncate">
                              {caseItem.title}
                            </p>
                            {caseItem.description && (
                              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                                {caseItem.description}
                              </p>
                            )}
                          </div>
                          <div className="ml-4 flex-shrink-0">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                caseItem.status === 'active'
                                  ? 'bg-success/10 text-success border border-success/20'
                                  : caseItem.status === 'closed'
                                  ? 'bg-muted text-muted-foreground border border-border'
                                  : 'bg-secondary/10 text-secondary border border-secondary/20'
                              }`}
                            >
                              {caseItem.status}
                            </span>
                          </div>
                        </div>
                        <div className="mt-2 sm:flex sm:justify-between">
                          <div className="sm:flex space-x-4">
                            {caseItem.case_type && (
                              <p className="flex items-center text-sm text-muted-foreground">
                                Type: {formatText(caseItem.case_type)}
                              </p>
                            )}
                            {caseItem.jurisdiction && (
                              <p className="flex items-center text-sm text-muted-foreground">
                                Jurisdiction: {formatText(caseItem.jurisdiction)}
                              </p>
                            )}
                          </div>
                          <div className="mt-2 sm:mt-0">
                            <p className="text-sm text-muted-foreground">
                              Created {new Date(caseItem.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    </Link>
                    <div className="flex items-center px-4 border-l border-border">
                      <button
                        onClick={(e) => handleDeleteClick(caseItem, e)}
                        className="p-2 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                        title="Delete case"
                      >
                        <svg
                          className="h-5 w-5"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth="1.5"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!loading && !error && total > 20 && (
          <div className="flex items-center justify-between border-t border-border bg-card px-4 py-3 sm:px-6 rounded-lg shadow-sm">
            <div className="flex flex-1 justify-between sm:hidden">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="relative inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-card-foreground hover:bg-accent disabled:opacity-50 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page * 20 >= total}
                className="relative ml-3 inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-card-foreground hover:bg-accent disabled:opacity-50 transition-colors"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-card-foreground">
                  Showing page <span className="font-medium">{page}</span> of{' '}
                  <span className="font-medium">{Math.ceil(total / 20)}</span>
                </p>
              </div>
              <div>
                <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="relative inline-flex items-center rounded-l-md px-3 py-2 text-muted-foreground border border-border hover:bg-accent disabled:opacity-50 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page * 20 >= total}
                    className="relative inline-flex items-center rounded-r-md px-3 py-2 text-muted-foreground border border-border hover:bg-accent disabled:opacity-50 transition-colors"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}

        <ConfirmDialog
          isOpen={deleteDialogOpen}
          onClose={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          title="Delete Case"
          message={
            caseToDelete
              ? `Are you sure you want to delete "${caseToDelete.title}"? This action cannot be undone and will permanently delete all associated documents and data.`
              : ''
          }
          confirmText={deleting ? 'Deleting...' : 'Delete'}
          cancelText="Cancel"
          variant="danger"
        />
      </div>
    </AppLayout>
  );
}
