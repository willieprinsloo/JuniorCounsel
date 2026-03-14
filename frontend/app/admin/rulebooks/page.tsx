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

// South African Jurisdictions
const SA_JURISDICTIONS = [
  'South Africa (National)',
  'Constitutional Court',
  'Supreme Court of Appeal',
  'Gauteng Division, Pretoria',
  'Gauteng Local Division, Johannesburg',
  'KwaZulu-Natal Division, Pietermaritzburg',
  'KwaZulu-Natal Local Division, Durban',
  'Western Cape Division, Cape Town',
  'Eastern Cape Division, Makhanda (Grahamstown)',
  'Eastern Cape Local Division, Port Elizabeth',
  'Free State Division, Bloemfontein',
  'Limpopo Division, Polokwane',
  'Mpumalanga Division, Mbombela',
  'Northern Cape Division, Kimberley',
  'North West Division, Mahikeng',
  'Labour Court',
  'Labour Appeal Court',
  'Land Claims Court',
  'Competition Appeal Court',
  'Electoral Court',
];

export default function AdminRulebooksPage() {
  const [rulebooks, setRulebooks] = useState<Rulebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedRulebook, setSelectedRulebook] = useState<Rulebook | null>(null);
  const [filterJurisdiction, setFilterJurisdiction] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [formData, setFormData] = useState<RulebookUpload | RulebookUpdate>({
    document_type: '',
    jurisdiction: '',
    version: '',
    source_yaml: '',
    label: '',
  });
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  const perPage = 20;

  const validateYAML = (yaml: string): boolean => {
    setYamlError(null);
    if (!yaml.trim()) {
      setYamlError('YAML content cannot be empty');
      return false;
    }

    // Basic YAML validation - check for common errors
    const lines = yaml.split('\n');
    let indentStack: number[] = [0];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().startsWith('#') || !line.trim()) continue; // Skip comments and empty lines

      const leadingSpaces = line.match(/^(\s*)/)?.[0].length || 0;

      // Check if indentation is consistent (multiples of 2)
      if (leadingSpaces % 2 !== 0) {
        setYamlError(`Line ${i + 1}: Inconsistent indentation (should be multiples of 2 spaces)`);
        return false;
      }
    }

    return true;
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        setFormData({ ...formData, source_yaml: content });
      };
      reader.readAsText(file);
    }
  };

  const downloadYAML = () => {
    if (!formData.source_yaml) {
      alert('No YAML content to download');
      return;
    }

    const blob = new Blob([formData.source_yaml], { type: 'text/yaml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const filename = selectedRulebook
      ? `${selectedRulebook.document_type}_${selectedRulebook.version}.yaml`
      : 'rulebook.yaml';
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const fetchRulebooks = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build params object, only include filters if they have values
      const params: any = {
        page,
        per_page: perPage,
      };

      if (filterJurisdiction) {
        params.jurisdiction = filterJurisdiction;
      }

      if (filterStatus) {
        params.status = filterStatus;
      }

      const response = await rulebooksAPI.list(params);
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
  }, [page, filterJurisdiction, filterStatus]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate YAML before submitting
    if (!validateYAML(formData.source_yaml || '')) {
      return;
    }

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
      setYamlError(null);
      fetchRulebooks();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to upload rulebook');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRulebook) return;

    // Validate YAML before submitting if it's being updated
    if (formData.source_yaml && !validateYAML(formData.source_yaml)) {
      return;
    }

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
      setYamlError(null);
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

  const openEditModal = async (rulebook: Rulebook) => {
    setSelectedRulebook(rulebook);

    try {
      // Fetch full rulebook details including YAML
      const fullRulebook = await adminRulebooksAPI.get(rulebook.id);

      setFormData({
        label: fullRulebook.label || '',
        source_yaml: fullRulebook.source_yaml || '',  // Pre-fill with existing YAML
      });
      setShowEditModal(true);
    } catch (err) {
      const apiError = err as APIError;
      console.error('Failed to load rulebook details:', apiError);
      alert(apiError.message || 'Failed to load rulebook details for editing');
    }
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

      {/* Filters */}
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Filter by Jurisdiction
            </label>
            <select
              value={filterJurisdiction}
              onChange={(e) => {
                setFilterJurisdiction(e.target.value);
                setPage(1); // Reset to first page
              }}
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
            >
              <option value="">All Jurisdictions</option>
              {SA_JURISDICTIONS.map((jurisdiction) => (
                <option key={jurisdiction} value={jurisdiction}>
                  {jurisdiction}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Filter by Status
            </label>
            <select
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setPage(1); // Reset to first page
              }}
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="deprecated">Deprecated</option>
            </select>
          </div>
          {(filterJurisdiction || filterStatus) && (
            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilterJurisdiction('');
                  setFilterStatus('');
                  setPage(1);
                }}
                className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
              >
                Clear Filters
              </button>
            </div>
          )}
        </div>
      </div>

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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
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
                    value={(formData as RulebookUpload).document_type || ''}
                    onChange={(e) => setFormData({ ...formData, document_type: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Jurisdiction *
                  </label>
                  <select
                    required
                    value={(formData as RulebookUpload).jurisdiction || ''}
                    onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                  >
                    <option value="">Select jurisdiction...</option>
                    {SA_JURISDICTIONS.map((jurisdiction) => (
                      <option key={jurisdiction} value={jurisdiction}>
                        {jurisdiction}
                      </option>
                    ))}
                  </select>
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
                    value={(formData as RulebookUpload).version || ''}
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
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-foreground">
                    YAML Content *
                  </label>
                  <div className="flex gap-2">
                    <label className="inline-flex items-center px-3 py-1.5 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted cursor-pointer transition-colors">
                      <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload File
                      <input
                        type="file"
                        accept=".yaml,.yml"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>
                    {formData.source_yaml && (
                      <button
                        type="button"
                        onClick={downloadYAML}
                        className="inline-flex items-center px-3 py-1.5 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted transition-colors"
                      >
                        <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  required
                  rows={25}
                  placeholder="Paste YAML rulebook content here or upload a file..."
                  value={formData.source_yaml || ''}
                  onChange={(e) => {
                    setFormData({ ...formData, source_yaml: e.target.value });
                    setYamlError(null);
                  }}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm resize-y"
                />
                {yamlError && (
                  <p className="mt-2 text-sm text-destructive">{yamlError}</p>
                )}
                <p className="mt-2 text-xs text-muted-foreground">
                  Tip: Use 2-space indentation. Lines: {formData.source_yaml?.split('\n').length || 0}
                </p>
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
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
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-foreground">
                    YAML Content
                  </label>
                  <div className="flex gap-2">
                    <label className="inline-flex items-center px-3 py-1.5 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted cursor-pointer transition-colors">
                      <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload File
                      <input
                        type="file"
                        accept=".yaml,.yml"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>
                    {formData.source_yaml && (
                      <button
                        type="button"
                        onClick={downloadYAML}
                        className="inline-flex items-center px-3 py-1.5 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted transition-colors"
                      >
                        <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  rows={25}
                  placeholder="Edit YAML content..."
                  value={formData.source_yaml || ''}
                  onChange={(e) => {
                    setFormData({ ...formData, source_yaml: e.target.value });
                    setYamlError(null);
                  }}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm resize-y"
                />
                {yamlError && (
                  <p className="mt-2 text-sm text-destructive">{yamlError}</p>
                )}
                <p className="mt-2 text-xs text-muted-foreground">
                  Tip: Use 2-space indentation. Lines: {formData.source_yaml?.split('\n').length || 0}
                </p>
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
