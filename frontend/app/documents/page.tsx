'use client';

/**
 * Documents List Page
 *
 * Browse all documents across all cases.
 */

import { useState, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { documentsAPI } from '@/lib/api/services';
import { useAuth } from '@/lib/auth/context';
import type { Document } from '@/types/api';
import Link from 'next/link';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();

  useEffect(() => {
    const loadDocuments = async () => {
      if (!user) return;

      try {
        setLoading(true);
        // Note: This would need to be updated to fetch across all cases
        // For now, this is a placeholder implementation
        setDocuments([]);
      } catch (err) {
        setError('Failed to load documents');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, [user]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      queued: 'bg-secondary/10 text-secondary border border-secondary/20',
      processing: 'bg-secondary/10 text-secondary border border-secondary/20',
      completed: 'bg-success/10 text-success border border-success/20',
      failed: 'bg-destructive/10 text-destructive border border-destructive/20',
    };
    return colors[status] || 'bg-muted text-muted-foreground border border-border';
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">All Documents</h1>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading documents...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/30 p-4">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {!loading && !error && documents.length === 0 && (
          <div className="text-center py-12 bg-card border border-border rounded-lg shadow-sm">
            <p className="text-muted-foreground">No documents found.</p>
            <Link
              href="/cases"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
            >
              Go to Cases
            </Link>
          </div>
        )}

        {!loading && !error && documents.length > 0 && (
          <div className="bg-card border border-border shadow-sm overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-border">
              {documents.map((doc) => (
                <li key={doc.id} className="px-4 py-4 sm:px-6 hover:bg-accent/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/cases/${doc.case_id}`}
                        className="text-sm font-medium text-primary hover:text-primary/80 truncate transition-colors"
                      >
                        {doc.filename}
                      </Link>
                      <div className="mt-1 flex items-center space-x-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(doc.overall_status)}`}>
                          {doc.overall_status}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {doc.document_type}
                        </span>
                        {doc.pages && (
                          <span className="text-xs text-muted-foreground">
                            {doc.pages} pages
                          </span>
                        )}
                      </div>
                    </div>
                    {doc.stage_progress > 0 && doc.overall_status === 'processing' && (
                      <div className="ml-4 flex-shrink-0">
                        <div className="text-xs text-muted-foreground">
                          {doc.stage_progress}%
                        </div>
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
