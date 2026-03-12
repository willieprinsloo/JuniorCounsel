'use client';

/**
 * Draft Detail Page
 *
 * View and manage a draft session with intake, generation, and citations.
 */

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { draftSessionsAPI } from '@/lib/api/services';
import type { DraftSession, Citation } from '@/types/api';

export default function DraftDetailPage() {
  const params = useParams();
  const router = useRouter();
  const draftId = params.id as string;

  const [draft, setDraft] = useState<DraftSession | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'draft' | 'citations'>('draft');

  const [intakeResponses, setIntakeResponses] = useState<Record<string, any>>({});
  const [submittingIntake, setSubmittingIntake] = useState(false);
  const [startingGeneration, setStartingGeneration] = useState(false);

  useEffect(() => {
    loadDraftData();
    const interval = setInterval(loadDraftData, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [draftId]);

  const loadDraftData = async () => {
    try {
      const draftData = await draftSessionsAPI.get(draftId);
      setDraft(draftData);

      // Load citations if draft is ready
      if (draftData.status === 'ready' || draftData.status === 'review') {
        try {
          const citationsData = await draftSessionsAPI.getCitations(draftId);
          setCitations(citationsData.citations);
        } catch (err) {
          console.error('Failed to load citations:', err);
        }
      }

      setLoading(false);
    } catch (err) {
      setError('Failed to load draft');
      setLoading(false);
      console.error(err);
    }
  };

  const handleSubmitIntake = async () => {
    if (!draft) return;

    setSubmittingIntake(true);
    try {
      const updated = await draftSessionsAPI.submitIntake(draftId, {
        intake_responses: intakeResponses,
      });
      setDraft(updated);
    } catch (err) {
      console.error('Failed to submit intake:', err);
    } finally {
      setSubmittingIntake(false);
    }
  };

  const handleStartGeneration = async () => {
    setStartingGeneration(true);
    try {
      const updated = await draftSessionsAPI.startGeneration(draftId);
      setDraft(updated);
    } catch (err) {
      console.error('Failed to start generation:', err);
    } finally {
      setStartingGeneration(false);
    }
  };

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

  if (loading) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-gray-600">Loading draft...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !draft) {
    return (
      <AppLayout>
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error || 'Draft not found'}</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">{draft.title}</h1>
              <p className="mt-1 text-sm text-gray-600">
                {draft.document_type}
              </p>
            </div>
            <span className={`ml-4 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(draft.status)}`}>
              {draft.status.replace(/_/g, ' ')}
            </span>
          </div>

          {draft.error_message && (
            <div className="mt-4 rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{draft.error_message}</p>
            </div>
          )}
        </div>

        {/* Awaiting Intake */}
        {draft.status === 'awaiting_intake' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Answer a Few Questions
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              To help generate your draft, please answer the following questions about your case.
            </p>

            {/* Placeholder for intake form - would need rulebook schema */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Example Question
                </label>
                <textarea
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  rows={3}
                  value={intakeResponses['example'] || ''}
                  onChange={(e) => setIntakeResponses((prev) => ({ ...prev, example: e.target.value }))}
                  placeholder="Enter your answer here..."
                />
              </div>

              <div className="pt-4">
                <button
                  onClick={handleSubmitIntake}
                  disabled={submittingIntake}
                  className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {submittingIntake ? 'Submitting...' : 'Submit Answers'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Research Complete - Start Generation */}
        {draft.status === 'research' && draft.research_summary && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Research Complete
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              We've analyzed your case documents and are ready to generate the draft.
            </p>

            <button
              onClick={handleStartGeneration}
              disabled={startingGeneration}
              className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {startingGeneration ? 'Starting...' : 'Start Drafting'}
            </button>
          </div>
        )}

        {/* Processing Status */}
        {(draft.status === 'initializing' || draft.status === 'drafting') && (
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="animate-spin h-8 w-8 text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-lg font-medium text-gray-900">
                  {draft.status === 'initializing' ? 'Initializing...' : 'Drafting document...'}
                </p>
                <p className="text-sm text-gray-600">
                  This may take a few minutes. The page will update automatically.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Draft Ready */}
        {(draft.status === 'ready' || draft.status === 'review') && draft.draft_doc && (
          <>
            {/* Tabs */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('draft')}
                  className={`${
                    activeTab === 'draft'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                >
                  Draft Document
                </button>
                <button
                  onClick={() => setActiveTab('citations')}
                  className={`${
                    activeTab === 'citations'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                >
                  Citations ({citations.length})
                </button>
              </nav>
            </div>

            {/* Draft Content */}
            {activeTab === 'draft' && (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="prose max-w-none">
                  {draft.draft_doc.content ? (
                    <pre className="whitespace-pre-wrap font-serif">
                      {draft.draft_doc.content}
                    </pre>
                  ) : (
                    <p className="text-gray-600">No content available</p>
                  )}
                </div>
              </div>
            )}

            {/* Citations Tab */}
            {activeTab === 'citations' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Citations ({citations.length})
                  </h3>

                  {citations.length === 0 ? (
                    <p className="text-sm text-gray-600">No citations found.</p>
                  ) : (
                    <ul className="divide-y divide-gray-200">
                      {citations.map((citation, index) => (
                        <li key={index} className="py-4">
                          <div className="flex items-start">
                            <span className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-blue-100 text-blue-800 text-sm font-medium flex-shrink-0">
                              {citation.marker}
                            </span>
                            <div className="ml-4 flex-1">
                              <p className="text-sm font-medium text-gray-900">
                                {citation.document_name}
                                {citation.page && ` - Page ${citation.page}`}
                              </p>
                              <p className="mt-1 text-sm text-gray-600">
                                {citation.content}
                              </p>
                              {citation.similarity && (
                                <p className="mt-1 text-xs text-gray-500">
                                  Relevance: {(citation.similarity * 100).toFixed(1)}%
                                </p>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
