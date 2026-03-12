'use client';

/**
 * Case Detail Page
 *
 * View and manage a single case with documents and drafts.
 */

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { casesAPI, documentsAPI, draftSessionsAPI } from '@/lib/api/services';
import type { Case, Document, DraftSession } from '@/types/api';
import Link from 'next/link';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [draftSessions, setDraftSessions] = useState<DraftSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'documents' | 'drafts'>('documents');

  useEffect(() => {
    const loadCaseData = async () => {
      try {
        setLoading(true);

        // Load case details
        const caseResponse = await casesAPI.get(caseId);
        setCaseData(caseResponse);

        // Load documents
        const docsResponse = await documentsAPI.list({
          case_id: caseId,
          per_page: 50,
        });
        setDocuments(docsResponse.data);

        // Load draft sessions
        const draftsResponse = await draftSessionsAPI.list({
          case_id: caseId,
          per_page: 50,
        });
        setDraftSessions(draftsResponse.data);
      } catch (err) {
        setError('Failed to load case details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadCaseData();
  }, [caseId]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-100 text-green-800',
      closed: 'bg-gray-100 text-gray-800',
      archived: 'bg-yellow-100 text-yellow-800',
      queued: 'bg-blue-100 text-blue-800',
      processing: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      initializing: 'bg-blue-100 text-blue-800',
      awaiting_intake: 'bg-purple-100 text-purple-800',
      research: 'bg-yellow-100 text-yellow-800',
      drafting: 'bg-yellow-100 text-yellow-800',
      review: 'bg-orange-100 text-orange-800',
      ready: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-gray-600">Loading case...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !caseData) {
    return (
      <AppLayout>
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error || 'Case not found'}</p>
          <button
            onClick={() => router.push('/cases')}
            className="mt-4 text-sm text-red-600 hover:text-red-800"
          >
            Back to Cases
          </button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Case Header */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">{caseData.title}</h1>
              {caseData.description && (
                <p className="mt-2 text-sm text-gray-600">{caseData.description}</p>
              )}
            </div>
            <span className={`ml-4 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(caseData.status)}`}>
              {caseData.status}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {caseData.case_type && (
              <div>
                <p className="text-xs text-gray-500">Case Type</p>
                <p className="text-sm font-medium text-gray-900">{caseData.case_type}</p>
              </div>
            )}
            {caseData.jurisdiction && (
              <div>
                <p className="text-xs text-gray-500">Jurisdiction</p>
                <p className="text-sm font-medium text-gray-900">{caseData.jurisdiction}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-gray-500">Created</p>
              <p className="text-sm font-medium text-gray-900">
                {new Date(caseData.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('documents')}
              className={`${
                activeTab === 'documents'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Documents ({documents.length})
            </button>
            <button
              onClick={() => setActiveTab('drafts')}
              className={`${
                activeTab === 'drafts'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Drafts ({draftSessions.length})
            </button>
          </nav>
        </div>

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Link
                href={`/cases/${caseId}/upload`}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Upload Documents
              </Link>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <p className="text-gray-600">No documents uploaded yet.</p>
              </div>
            ) : (
              <div className="bg-white shadow overflow-hidden sm:rounded-md">
                <ul className="divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <li key={doc.id} className="px-4 py-4 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {doc.filename}
                          </p>
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
        )}

        {/* Drafts Tab */}
        {activeTab === 'drafts' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Link
                href={`/cases/${caseId}/new-draft`}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                New Draft
              </Link>
            </div>

            {draftSessions.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <p className="text-gray-600">No drafts created yet.</p>
              </div>
            ) : (
              <div className="bg-white shadow overflow-hidden sm:rounded-md">
                <ul className="divide-y divide-gray-200">
                  {draftSessions.map((draft) => (
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
                                {draft.status}
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
        )}
      </div>
    </AppLayout>
  );
}
