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
      active: 'bg-success/10 text-success border border-success/20',
      closed: 'bg-muted text-card-foreground border border-border',
      archived: 'bg-secondary/10 text-secondary border border-secondary/20',
      queued: 'bg-secondary/10 text-secondary border border-secondary/20',
      processing: 'bg-secondary/10 text-secondary border border-secondary/20',
      completed: 'bg-success/10 text-success border border-success/20',
      failed: 'bg-destructive/10 text-destructive border border-destructive/20',
      initializing: 'bg-secondary/10 text-secondary border border-secondary/20',
      awaiting_intake: 'bg-secondary/10 text-secondary border border-secondary/20',
      research: 'bg-secondary/10 text-secondary border border-secondary/20',
      drafting: 'bg-secondary/10 text-secondary border border-secondary/20',
      review: 'bg-secondary/10 text-secondary border border-secondary/20',
      ready: 'bg-success/10 text-success border border-success/20',
    };
    return colors[status] || 'bg-muted text-card-foreground border border-border';
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading case...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !caseData) {
    return (
      <AppLayout>
        <div className="rounded-md bg-destructive/10 p-4 border border-destructive/20">
          <p className="text-sm text-destructive">{error || 'Case not found'}</p>
          <button
            onClick={() => router.push('/cases')}
            className="mt-4 text-sm text-destructive hover:text-destructive/90 transition-colors"
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
        <div className="bg-card shadow rounded-lg p-6 border border-border">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-foreground">{caseData.title}</h1>
              {caseData.description && (
                <p className="mt-2 text-sm text-muted-foreground">{caseData.description}</p>
              )}
            </div>
            <span className={`ml-4 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(caseData.status)}`}>
              {caseData.status}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {caseData.case_type && (
              <div>
                <p className="text-xs text-muted-foreground">Case Type</p>
                <p className="text-sm font-medium text-foreground">{caseData.case_type}</p>
              </div>
            )}
            {caseData.jurisdiction && (
              <div>
                <p className="text-xs text-muted-foreground">Jurisdiction</p>
                <p className="text-sm font-medium text-foreground">{caseData.jurisdiction}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="text-sm font-medium text-foreground">
                {new Date(caseData.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-border">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('documents')}
              className={`${
                activeTab === 'documents'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
            >
              Documents ({documents.length})
            </button>
            <button
              onClick={() => setActiveTab('drafts')}
              className={`${
                activeTab === 'drafts'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
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
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
              >
                Upload Documents
              </Link>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-12 bg-card rounded-lg shadow border border-border">
                <p className="text-muted-foreground">No documents uploaded yet.</p>
              </div>
            ) : (
              <div className="bg-card shadow overflow-hidden sm:rounded-md border border-border">
                <ul className="divide-y divide-border">
                  {documents.map((doc) => (
                    <li key={doc.id} className="px-4 py-4 sm:px-6">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">
                              {doc.filename}
                            </p>
                            <div className="mt-1 flex items-center space-x-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(doc.overall_status)}`}>
                                {doc.overall_status}
                              </span>
                              {doc.stage && doc.overall_status === 'processing' && (
                                <span className="text-xs text-muted-foreground">
                                  {doc.stage.replace('_', ' ')}
                                </span>
                              )}
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
                          <div className="ml-4 flex-shrink-0 flex items-center space-x-2">
                            {doc.stage_progress > 0 && doc.overall_status === 'processing' && (
                              <div className="text-xs text-muted-foreground">
                                {doc.stage_progress}%
                              </div>
                            )}
                            {doc.overall_status === 'failed' && (
                              <button
                                onClick={async () => {
                                  try {
                                    await documentsAPI.retry(doc.id);
                                    // Reload documents
                                    const docsResponse = await documentsAPI.list({
                                      case_id: caseId,
                                      per_page: 50,
                                    });
                                    setDocuments(docsResponse.data);
                                  } catch (err) {
                                    console.error('Failed to retry:', err);
                                  }
                                }}
                                className="inline-flex items-center px-3 py-1.5 border border-border text-xs font-medium rounded-md text-foreground bg-card hover:bg-accent transition-colors"
                              >
                                Retry
                              </button>
                            )}
                            <button
                              onClick={async () => {
                                if (confirm(`Delete ${doc.filename}? This will remove the file and all associated data.`)) {
                                  try {
                                    await documentsAPI.delete(doc.id);
                                    // Remove from list
                                    setDocuments(docs => docs.filter(d => d.id !== doc.id));
                                  } catch (err) {
                                    console.error('Failed to delete:', err);
                                  }
                                }
                              }}
                              className="inline-flex items-center px-3 py-1.5 border border-destructive/20 text-xs font-medium rounded-md text-destructive bg-card hover:bg-destructive/10 transition-colors"
                            >
                              Delete
                            </button>
                          </div>
                        </div>

                        {/* Progress bar for processing documents */}
                        {doc.overall_status === 'processing' && (
                          <div className="w-full bg-muted rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all duration-300"
                              style={{ width: `${doc.stage_progress}%` }}
                            ></div>
                          </div>
                        )}

                        {/* Error message for failed documents */}
                        {doc.overall_status === 'failed' && doc.error_message && (
                          <div className="bg-destructive/5 border border-destructive/20 rounded-md p-3">
                            <p className="text-xs font-medium text-destructive mb-1">Error:</p>
                            <p className="text-xs text-destructive/90">{doc.error_message}</p>
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
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
              >
                New Draft
              </Link>
            </div>

            {draftSessions.length === 0 ? (
              <div className="text-center py-12 bg-card rounded-lg shadow border border-border">
                <p className="text-muted-foreground">No drafts created yet.</p>
              </div>
            ) : (
              <div className="bg-card shadow overflow-hidden sm:rounded-md border border-border">
                <ul className="divide-y divide-border">
                  {draftSessions.map((draft) => (
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
                                {draft.status}
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
        )}
      </div>
    </AppLayout>
  );
}
