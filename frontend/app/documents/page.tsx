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
      queued: 'bg-blue-100 text-blue-800',
      processing: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">All Documents</h1>
        </div>

        {loading && (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading documents...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {!loading && !error && documents.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No documents found.</p>
            <Link
              href="/cases"
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200"
            >
              Go to Cases
            </Link>
          </div>
        )}

        {!loading && !error && documents.length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {documents.map((doc) => (
                <li key={doc.id} className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/cases/${doc.case_id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800 truncate"
                      >
                        {doc.filename}
                      </Link>
                      <div className="mt-1 flex items-center space-x-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(doc.overall_status)}`}>
                          {doc.overall_status}
                        </span>
                        <span className="text-xs text-gray-500">
                          {doc.document_type}
                        </span>
                        {doc.pages && (
                          <span className="text-xs text-gray-500">
                            {doc.pages} pages
                          </span>
                        )}
                      </div>
                    </div>
                    {doc.stage_progress > 0 && doc.overall_status === 'processing' && (
                      <div className="ml-4 flex-shrink-0">
                        <div className="text-xs text-gray-500">
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
