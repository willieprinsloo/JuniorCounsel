'use client';

/**
 * New Case Creation Page
 *
 * Form for creating a new legal case.
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { casesAPI } from '@/lib/api/services';
import { CaseStatus } from '@/types/api';

export default function NewCasePage() {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    case_type: '',
    jurisdiction: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCreating(true);

    try {
      // TODO: Get organisation_id from user context
      const caseData = await casesAPI.create({
        organisation_id: 1, // Placeholder
        title: formData.title,
        description: formData.description || undefined,
        case_type: formData.case_type || undefined,
        jurisdiction: formData.jurisdiction || undefined,
      });

      // Redirect to case detail
      router.push(`/cases/${caseData.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create case');
      setCreating(false);
    }
  };

  const caseTypes = [
    'Civil Litigation',
    'Commercial Dispute',
    'Family Law',
    'Labour Dispute',
    'Criminal Defense',
    'Constitutional Matter',
    'Administrative Law',
    'Other',
  ];

  const jurisdictions = [
    'High Court - Gauteng Division',
    'High Court - Western Cape Division',
    'High Court - KwaZulu-Natal Division',
    'High Court - Eastern Cape Division',
    'Magistrate Court',
    'Labour Court',
    'Constitutional Court',
    'Supreme Court of Appeal',
    'Other',
  ];

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create New Case</h1>
          <p className="mt-1 text-sm text-gray-600">
            Start a new legal case to organize documents and drafts.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6 space-y-6">
            {/* Title */}
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                Case Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="title"
                required
                value={formData.title}
                onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="e.g., Smith v Jones - Application for Divorce"
                disabled={creating}
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                rows={4}
                value={formData.description}
                onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="Brief description of the case..."
                disabled={creating}
              />
            </div>

            {/* Case Type */}
            <div>
              <label htmlFor="case_type" className="block text-sm font-medium text-gray-700">
                Case Type
              </label>
              <select
                id="case_type"
                value={formData.case_type}
                onChange={(e) => setFormData((prev) => ({ ...prev, case_type: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                disabled={creating}
              >
                <option value="">Select a case type...</option>
                {caseTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            {/* Jurisdiction */}
            <div>
              <label htmlFor="jurisdiction" className="block text-sm font-medium text-gray-700">
                Jurisdiction
              </label>
              <select
                id="jurisdiction"
                value={formData.jurisdiction}
                onChange={(e) => setFormData((prev) => ({ ...prev, jurisdiction: e.target.value }))}
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

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
          </div>

          <div className="px-4 py-3 bg-gray-50 text-right sm:px-6 rounded-b-lg space-x-3">
            <button
              type="button"
              onClick={() => router.push('/cases')}
              disabled={creating}
              className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !formData.title}
              className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
}
