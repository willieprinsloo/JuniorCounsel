'use client';

/**
 * New Draft Creation Page
 *
 * Wizard for creating a new draft session.
 */

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { draftSessionsAPI, rulebooksAPI } from '@/lib/api/services';
import type { Rulebook } from '@/types/api';

export default function NewDraftPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [rulebooks, setRulebooks] = useState<Rulebook[]>([]);
  const [loadingRulebooks, setLoadingRulebooks] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    title: '',
    document_type: '',
    jurisdiction: '',
    rulebook_id: 0,
  });

  useEffect(() => {
    const loadRulebooks = async () => {
      try {
        const response = await rulebooksAPI.list({
          status: 'published',
          per_page: 100,
        });
        setRulebooks(response.data);
      } catch (err) {
        console.error('Failed to load rulebooks:', err);
      } finally {
        setLoadingRulebooks(false);
      }
    };

    loadRulebooks();
  }, []);

  const handleDocumentTypeChange = (documentType: string) => {
    setFormData((prev) => ({
      ...prev,
      document_type: documentType,
      jurisdiction: '',
      rulebook_id: 0,
    }));
  };

  const handleJurisdictionChange = (jurisdiction: string) => {
    setFormData((prev) => ({
      ...prev,
      jurisdiction,
      rulebook_id: 0,
    }));

    // Auto-select rulebook if there's only one match
    const matchingRulebooks = rulebooks.filter(
      (rb) => rb.document_type === formData.document_type && rb.jurisdiction === jurisdiction
    );

    if (matchingRulebooks.length === 1) {
      setFormData((prev) => ({
        ...prev,
        rulebook_id: matchingRulebooks[0].id,
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCreating(true);

    try {
      const draftSession = await draftSessionsAPI.create({
        case_id: caseId,
        rulebook_id: formData.rulebook_id,
        title: formData.title,
        document_type: formData.document_type,
      });

      // Redirect to draft detail page
      router.push(`/drafts/${draftSession.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create draft');
      setCreating(false);
    }
  };

  const documentTypes = Array.from(new Set(rulebooks.map((rb) => rb.document_type)));
  const jurisdictions = formData.document_type
    ? Array.from(new Set(rulebooks.filter((rb) => rb.document_type === formData.document_type).map((rb) => rb.jurisdiction)))
    : [];
  const availableRulebooks = formData.jurisdiction
    ? rulebooks.filter((rb) => rb.document_type === formData.document_type && rb.jurisdiction === formData.jurisdiction)
    : [];

  const isValid = formData.title && formData.document_type && formData.jurisdiction && formData.rulebook_id > 0;

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create New Draft</h1>
          <p className="mt-1 text-sm text-gray-600">
            Start a new document drafting session for this case.
          </p>
        </div>

        {loadingRulebooks ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading document templates...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6 space-y-6">
              {/* Title */}
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                  Draft Title
                </label>
                <input
                  type="text"
                  id="title"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  placeholder="e.g., Founding Affidavit - Application for Divorce"
                  disabled={creating}
                />
              </div>

              {/* Document Type */}
              <div>
                <label htmlFor="document_type" className="block text-sm font-medium text-gray-700">
                  Document Type
                </label>
                <select
                  id="document_type"
                  required
                  value={formData.document_type}
                  onChange={(e) => handleDocumentTypeChange(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  disabled={creating}
                >
                  <option value="">Select a document type...</option>
                  {documentTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              {/* Jurisdiction */}
              {formData.document_type && (
                <div>
                  <label htmlFor="jurisdiction" className="block text-sm font-medium text-gray-700">
                    Jurisdiction
                  </label>
                  <select
                    id="jurisdiction"
                    required
                    value={formData.jurisdiction}
                    onChange={(e) => handleJurisdictionChange(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                    disabled={creating}
                  >
                    <option value="">Select a jurisdiction...</option>
                    {jurisdictions.map((jurisdiction) => (
                      <option key={jurisdiction} value={jurisdiction}>
                        {jurisdiction}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Rulebook */}
              {formData.jurisdiction && availableRulebooks.length > 0 && (
                <div>
                  <label htmlFor="rulebook_id" className="block text-sm font-medium text-gray-700">
                    Template Version
                  </label>
                  <select
                    id="rulebook_id"
                    required
                    value={formData.rulebook_id}
                    onChange={(e) => setFormData((prev) => ({ ...prev, rulebook_id: Number(e.target.value) }))}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                    disabled={creating}
                  >
                    <option value={0}>Select a template...</option>
                    {availableRulebooks.map((rb) => (
                      <option key={rb.id} value={rb.id}>
                        {rb.label || `Version ${rb.version}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}
            </div>

            <div className="px-4 py-3 bg-gray-50 text-right sm:px-6 rounded-b-lg space-x-3">
              <button
                type="button"
                onClick={() => router.push(`/cases/${caseId}`)}
                disabled={creating}
                className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!isValid || creating}
                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create Draft'}
              </button>
            </div>
          </form>
        )}
      </div>
    </AppLayout>
  );
}
