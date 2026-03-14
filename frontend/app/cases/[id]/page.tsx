'use client';

/**
 * Case Detail Page
 *
 * View and manage a single case with documents and drafts.
 */

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { casesAPI, documentsAPI, draftSessionsAPI, usageAPI } from '@/lib/api/services';
import { DocumentAssistantSidebar } from '@/components/chat/DocumentAssistantSidebar';
import type { Case, Document, DraftSession, UsageSummary } from '@/types/api';
import Link from 'next/link';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [draftSessions, setDraftSessions] = useState<DraftSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'documents' | 'drafts'>('documents');
  const [documentUsage, setDocumentUsage] = useState<Record<string, UsageSummary>>({});
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Load case data
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

  // Check for success message in URL params
  useEffect(() => {
    const success = searchParams.get('success');
    const message = searchParams.get('message');

    if (success === 'true' && message) {
      setSuccessMessage(decodeURIComponent(message));
      setShowSuccessBanner(true);

      // Auto-hide after 10 seconds
      const timer = setTimeout(() => {
        setShowSuccessBanner(false);
      }, 10000);

      // Clear URL params
      router.replace(`/cases/${caseId}`, { scroll: false });

      return () => clearTimeout(timer);
    }
  }, [searchParams, caseId, router]);

  // Auto-refresh documents when processing
  useEffect(() => {
    // Check if any documents are processing
    const hasProcessingDocs = documents.some(
      doc => doc.overall_status === 'processing' || doc.overall_status === 'queued'
    );

    if (!hasProcessingDocs || activeTab !== 'documents') {
      return;
    }

    // Poll every 3 seconds for status updates
    const interval = setInterval(async () => {
      try {
        const docsResponse = await documentsAPI.list({
          case_id: caseId,
          per_page: 50,
        });
        setDocuments(docsResponse.data);
      } catch (err) {
        console.error('Failed to refresh documents:', err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, caseId, activeTab]);

  // Auto-refresh drafts when processing
  useEffect(() => {
    // Check if any drafts are in progress
    const hasProcessingDrafts = draftSessions.some(
      draft => draft.status === 'research' || draft.status === 'drafting'
    );

    if (!hasProcessingDrafts || activeTab !== 'drafts') {
      return;
    }

    // Poll every 3 seconds for status updates
    const interval = setInterval(async () => {
      try {
        const draftsResponse = await draftSessionsAPI.list({
          case_id: caseId,
          per_page: 50,
        });
        setDraftSessions(draftsResponse.data);
      } catch (err) {
        console.error('Failed to refresh drafts:', err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [draftSessions, caseId, activeTab]);

  // Load token usage for completed documents
  useEffect(() => {
    const loadDocumentUsage = async () => {
      for (const doc of documents) {
        if (doc.overall_status === 'completed' && !documentUsage[doc.id]) {
          try {
            const usage = await usageAPI.getDocumentUsage(doc.id);
            setDocumentUsage(prev => ({ ...prev, [doc.id]: usage }));
          } catch (err) {
            console.error(`Failed to load usage for document ${doc.id}:`, err);
          }
        }
      }
    };

    loadDocumentUsage();
  }, [documents, documentUsage]);

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
        {/* Success Banner */}
        {showSuccessBanner && (
          <div className="bg-success/10 border-l-4 border-success p-4 rounded-r-md shadow-sm animate-in slide-in-from-top duration-300">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-success" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-success">
                  {successMessage}
                </p>
              </div>
              <button
                onClick={() => setShowSuccessBanner(false)}
                className="flex-shrink-0 ml-4 text-success hover:text-success/80 transition-colors"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        )}

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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Document List (Left - 70%) */}
            <div className="lg:col-span-2 space-y-4">
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
                                {documentUsage[doc.id] && (
                                  <span className="text-xs text-muted-foreground">
                                    {documentUsage[doc.id].total_tokens.toLocaleString()} tokens (${documentUsage[doc.id].total_cost_usd.toFixed(4)})
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

            {/* Document Assistant Sidebar (Right - 30%) */}
            <div className="lg:col-span-1">
              <div className="sticky top-4">
                <DocumentAssistantSidebar
                  caseId={caseId}
                  documents={documents}
                  onDraftCreated={(draftId) => {
                    // Navigate to the newly created draft
                    router.push(`/drafts/${draftId}`);
                  }}
                />
              </div>
            </div>
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
                    <li key={draft.id} className="px-4 py-4 sm:px-6">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <Link
                              href={`/drafts/${draft.id}`}
                              className="text-sm font-medium text-primary hover:text-primary/90 truncate transition-colors"
                            >
                              {draft.title}
                            </Link>
                            <div className="mt-1 flex items-center space-x-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(draft.status)}`}>
                                {/* Show spinner for processing states */}
                                {(draft.status === 'research' || draft.status === 'drafting' || draft.status === 'initializing') && (
                                  <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                )}
                                {draft.status.replace('_', ' ')}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {draft.document_type}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4 flex-shrink-0 flex items-center space-x-2">
                            <span className="text-xs text-muted-foreground">
                              {new Date(draft.created_at).toLocaleDateString()}
                            </span>
                            {draft.status === 'failed' && (
                              <button
                                onClick={async (e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  try {
                                    await draftSessionsAPI.startGeneration(draft.id);
                                    // Reload drafts
                                    const draftsResponse = await draftSessionsAPI.list({
                                      case_id: caseId,
                                      per_page: 50,
                                    });
                                    setDraftSessions(draftsResponse.data);
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
                              onClick={async (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                if (confirm(`Delete "${draft.title}"? This will permanently remove the draft session.`)) {
                                  try {
                                    await draftSessionsAPI.delete(draft.id);
                                    // Remove from list
                                    setDraftSessions(drafts => drafts.filter(d => d.id !== draft.id));
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

                        {/* Error message for failed drafts */}
                        {draft.status === 'failed' && draft.error_message && (
                          <div className="bg-destructive/5 border border-destructive/20 rounded-md p-3">
                            <p className="text-xs font-medium text-destructive mb-1">Error:</p>
                            <p className="text-xs text-destructive/90">{draft.error_message}</p>
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
      </div>
    </AppLayout>
  );
}
