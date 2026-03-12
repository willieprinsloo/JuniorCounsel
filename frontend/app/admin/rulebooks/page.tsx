'use client';

/**
 * Admin Rulebook Management Page
 *
 * Manage rulebooks (upload, publish, deprecate).
 */

import { useState, useEffect } from 'react';
import { adminRulebooksAPI, rulebooksAPI } from '@/lib/api/services';
import { APIError } from '@/lib/api/client';
import type {
  Rulebook,
  RulebookUpload,
  RulebookUpdate,
  RulebookStatus,
} from '@/types/api';

export default function AdminRulebooksPage() {
  const [rulebooks, setRulebooks] = useState<Rulebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedRulebook, setSelectedRulebook] = useState<Rulebook | null>(null);
  const [formData, setFormData] = useState<RulebookUpload | RulebookUpdate>({
    document_type: '',
    jurisdiction: '',
    version: '',
    source_yaml: '',
    label: '',
  });

  const perPage = 20;

  const fetchRulebooks = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await rulebooksAPI.list({
        page,
        per_page: perPage,
      });
      setRulebooks(response.data);
      setTotal(response.total);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError.message || 'Failed to fetch rulebooks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRulebooks();
  }, [page]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminRulebooksAPI.upload(formData as RulebookUpload);
      setShowUploadModal(false);
      setFormData({
        document_type: '',
        jurisdiction: '',
        version: '',
        source_yaml: '',
        label: '',
      });
      fetchRulebooks();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to upload rulebook');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRulebook) return;
    try {
      await adminRulebooksAPI.update(selectedRulebook.id, formData as RulebookUpdate);
      setShowEditModal(false);
      setSelectedRulebook(null);
      setFormData({
        document_type: '',
        jurisdiction: '',
        version: '',
        source_yaml: '',
        label: '',
      });
      fetchRulebooks();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to update rulebook');
    }
  };

  const handlePublish = async (rulebookId: number) => {
    if (!confirm('Are you sure you want to publish this rulebook? It will become available for use.')) return;
    try {
      await adminRulebooksAPI.publish(rulebookId);
      fetchRulebooks();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to publish rulebook');
    }
  };

  const handleDeprecate = async (rulebookId: number) => {
    if (!confirm('Are you sure you want to deprecate this rulebook? It will no longer be available for new draft sessions.')) return;
    try {
      await adminRulebooksAPI.deprecate(rulebookId);
      fetchRulebooks();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to deprecate rulebook');
    }
  };

  const openEditModal = (rulebook: Rulebook) => {
    setSelectedRulebook(rulebook);
    setFormData({
      label: rulebook.label || '',
      source_yaml: '', // We don't have this in the list response
    });
    setShowEditModal(true);
  };

  const getStatusBadge = (status: RulebookStatus) => {
    switch (status) {
      case 'draft':
        return <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">Draft</span>;
      case 'published':
        return <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">Published</span>;
      case 'deprecated':
        return <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400">Deprecated</span>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Rulebook Management</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Upload and manage document type rulebooks (YAML configurations)
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          Upload Rulebook
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Rulebooks Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-2 text-sm text-muted-foreground">Loading rulebooks...</p>
        </div>
      ) : rulebooks.length === 0 ? (
        <div className="text-center py-12 bg-card border border-border rounded-lg">
          <p className="text-muted-foreground">No rulebooks found</p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Document Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Jurisdiction
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Version
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Label
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rulebooks.map((rulebook) => (
                <tr key={rulebook.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-card-foreground">
                      {rulebook.document_type}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-muted-foreground">{rulebook.jurisdiction}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-muted-foreground">{rulebook.version}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-muted-foreground">
                      {rulebook.label || <span className="italic">No label</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(rulebook.status)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                    {new Date(rulebook.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    {rulebook.status === 'draft' && (
                      <>
                        <button
                          onClick={() => openEditModal(rulebook)}
                          className="text-primary hover:text-primary/80"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handlePublish(rulebook.id)}
                          className="text-green-600 hover:text-green-700 dark:text-green-400"
                        >
                          Publish
                        </button>
                      </>
                    )}
                    {rulebook.status === 'published' && (
                      <button
                        onClick={() => handleDeprecate(rulebook.id)}
                        className="text-destructive hover:text-destructive/80"
                      >
                        Deprecate
                      </button>
                    )}
                    {rulebook.status === 'deprecated' && (
                      <span className="text-muted-foreground italic">No actions</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > perPage && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * perPage + 1} to {Math.min(page * perPage, total)} of {total} rulebooks
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page * perPage >= total}
              className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Upload Rulebook Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-xl font-bold text-card-foreground mb-4">Upload New Rulebook</h2>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Document Type *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., affidavit, pleading"
                    value={formData.document_type || ''}
                    onChange={(e) => setFormData({ ...formData, document_type: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Jurisdiction *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., South Africa"
                    value={formData.jurisdiction || ''}
                    onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Version *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., 1.0.0"
                    value={formData.version || ''}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Label
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Founding Affidavit"
                    value={formData.label || ''}
                    onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  YAML Content *
                </label>
                <textarea
                  required
                  rows={12}
                  placeholder="Paste YAML rulebook content here..."
                  value={formData.source_yaml || ''}
                  onChange={(e) => setFormData({ ...formData, source_yaml: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm"
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowUploadModal(false);
                    setFormData({
                      document_type: '',
                      jurisdiction: '',
                      version: '',
                      source_yaml: '',
                      label: '',
                    });
                  }}
                  className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Upload
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Rulebook Modal */}
      {showEditModal && selectedRulebook && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-xl font-bold text-card-foreground mb-4">Edit Rulebook (Draft Only)</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Only DRAFT rulebooks can be edited. To update a PUBLISHED rulebook, create a new version.
            </p>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Label</label>
                <input
                  type="text"
                  value={formData.label || ''}
                  onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  YAML Content (leave blank to keep current)
                </label>
                <textarea
                  rows={12}
                  placeholder="Paste new YAML content or leave blank..."
                  value={formData.source_yaml || ''}
                  onChange={(e) => setFormData({ ...formData, source_yaml: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm"
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedRulebook(null);
                    setFormData({
                      document_type: '',
                      jurisdiction: '',
                      version: '',
                      source_yaml: '',
                      label: '',
                    });
                  }}
                  className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Update
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
