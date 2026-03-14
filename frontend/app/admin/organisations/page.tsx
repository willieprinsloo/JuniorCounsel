'use client';

/**
 * Admin Organisation Management Page
 *
 * Comprehensive organisation management with CRUD and member management.
 */

import { useState, useEffect } from 'react';
import { adminOrganisationsAPI, adminUsersAPI } from '@/lib/api/services';
import { APIError } from '@/lib/api/client';
import type {
  Organisation,
  OrganisationCreate,
  OrganisationUpdate,
  OrganisationMember,
  OrganisationMemberAdd,
  OrganisationMemberUpdate,
  OrganisationRole,
  AdminUser,
} from '@/types/api';

export default function AdminOrganisationsPage() {
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showMembersModal, setShowMembersModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<Organisation | null>(null);
  const [members, setMembers] = useState<OrganisationMember[]>([]);
  const [availableUsers, setAvailableUsers] = useState<AdminUser[]>([]);
  const [formData, setFormData] = useState<OrganisationCreate | OrganisationUpdate>({
    name: '',
    contact_email: '',
    is_active: true,
  });
  const [memberFormData, setMemberFormData] = useState<OrganisationMemberAdd>({
    user_id: 0,
    role: 'practitioner' as OrganisationRole,
  });

  const perPage = 20;

  const fetchOrganisations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await adminOrganisationsAPI.list({
        page,
        per_page: perPage,
      });
      setOrganisations(response.data);
      setTotal(response.total);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError.message || 'Failed to fetch organisations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganisations();
  }, [page]);

  const fetchMembers = async (orgId: number) => {
    try {
      const response = await adminOrganisationsAPI.listMembers(orgId, {
        per_page: 100,
      });
      setMembers(response.data);
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to fetch members');
    }
  };

  const fetchAvailableUsers = async () => {
    try {
      const response = await adminUsersAPI.list({ per_page: 100 });
      setAvailableUsers(response.data);
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to fetch users');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminOrganisationsAPI.create(formData as OrganisationCreate);
      setShowCreateModal(false);
      setFormData({ name: '', contact_email: '', is_active: true });
      fetchOrganisations();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to create organisation');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      await adminOrganisationsAPI.update(selectedOrg.id, formData as OrganisationUpdate);
      setShowEditModal(false);
      setSelectedOrg(null);
      setFormData({ name: '', contact_email: '', is_active: true });
      fetchOrganisations();
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to update organisation');
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      await adminOrganisationsAPI.addMember(selectedOrg.id, memberFormData);
      setShowAddMemberModal(false);
      setMemberFormData({ user_id: 0, role: 'practitioner' as OrganisationRole });
      fetchMembers(selectedOrg.id);
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to add member');
    }
  };

  const handleRemoveMember = async (userId: number) => {
    if (!selectedOrg) return;
    if (!confirm('Are you sure you want to remove this member?')) return;
    try {
      await adminOrganisationsAPI.removeMember(selectedOrg.id, userId);
      fetchMembers(selectedOrg.id);
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to remove member');
    }
  };

  const handleUpdateMemberRole = async (userId: number, newRole: OrganisationRole) => {
    if (!selectedOrg) return;
    try {
      await adminOrganisationsAPI.updateMemberRole(selectedOrg.id, userId, { role: newRole });
      fetchMembers(selectedOrg.id);
    } catch (err) {
      const apiError = err as APIError;
      alert(apiError.message || 'Failed to update role');
    }
  };

  const openEditModal = (org: Organisation) => {
    setSelectedOrg(org);
    setFormData({
      name: org.name,
      contact_email: org.contact_email || '',
      is_active: org.is_active,
    });
    setShowEditModal(true);
  };

  const openMembersModal = async (org: Organisation) => {
    setSelectedOrg(org);
    await fetchMembers(org.id);
    setShowMembersModal(true);
  };

  const openAddMemberModal = async () => {
    await fetchAvailableUsers();
    setShowAddMemberModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Organisation Management</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Manage law firms, chambers, and their members
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Create Organisation
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Organisations Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-2 text-sm text-muted-foreground">Loading organisations...</p>
        </div>
      ) : organisations.length === 0 ? (
        <div className="text-center py-12 bg-card border border-border rounded-lg">
          <p className="text-muted-foreground">No organisations found</p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Organisation
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Contact
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
              {organisations.map((org) => (
                <tr key={org.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-card-foreground">{org.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-muted-foreground">
                      {org.contact_email || <span className="italic">No contact</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        org.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                      }`}
                    >
                      {org.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                    {new Date(org.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => openMembersModal(org)}
                      className="text-primary hover:text-primary/80"
                    >
                      Members
                    </button>
                    <button
                      onClick={() => openEditModal(org)}
                      className="text-primary hover:text-primary/80"
                    >
                      Edit
                    </button>
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
            Showing {(page - 1) * perPage + 1} to {Math.min(page * perPage, total)} of {total} organisations
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

      {/* Create Organisation Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-card-foreground mb-4">Create New Organisation</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Contact Email</label>
                <input
                  type="email"
                  value={formData.contact_email || ''}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                />
                <label htmlFor="is_active" className="ml-2 block text-sm text-foreground">
                  Active
                </label>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setFormData({ name: '', contact_email: '', is_active: true });
                  }}
                  className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Organisation Modal */}
      {showEditModal && selectedOrg && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-card-foreground mb-4">Edit Organisation</h2>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Contact Email</label>
                <input
                  type="email"
                  value={formData.contact_email || ''}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active_edit"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                />
                <label htmlFor="is_active_edit" className="ml-2 block text-sm text-foreground">
                  Active
                </label>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedOrg(null);
                    setFormData({ name: '', contact_email: '', is_active: true });
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

      {/* Members Modal */}
      {showMembersModal && selectedOrg && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-3xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-card-foreground">
                Members of {selectedOrg.name}
              </h2>
              <button
                onClick={openAddMemberModal}
                className="inline-flex items-center px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
              >
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add Member
              </button>
            </div>

            {members.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">No members yet</p>
            ) : (
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">User</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Role</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Joined</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {members.map((member) => (
                    <tr key={member.id}>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium">{member.full_name || 'No name'}</div>
                        <div className="text-xs text-muted-foreground">{member.email}</div>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={member.role}
                          onChange={(e) => handleUpdateMemberRole(member.user_id, e.target.value as OrganisationRole)}
                          className="text-sm px-2 py-1 border border-border rounded bg-background"
                        >
                          <option value="admin">Admin</option>
                          <option value="practitioner">Practitioner</option>
                          <option value="staff">Staff</option>
                        </select>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : <span className="italic">N/A</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleRemoveMember(member.user_id)}
                          className="text-destructive hover:text-destructive/80 text-sm"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <div className="flex justify-end mt-6">
              <button
                onClick={() => {
                  setShowMembersModal(false);
                  setSelectedOrg(null);
                  setMembers([]);
                }}
                className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showAddMemberModal && selectedOrg && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-card-foreground mb-4">Add Member</h2>
            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">User *</label>
                <select
                  required
                  value={memberFormData.user_id}
                  onChange={(e) => setMemberFormData({ ...memberFormData, user_id: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                >
                  <option value={0}>Select a user...</option>
                  {availableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.email} - {user.full_name || 'No name'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Role *</label>
                <select
                  value={memberFormData.role}
                  onChange={(e) => setMemberFormData({ ...memberFormData, role: e.target.value as OrganisationRole })}
                  className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
                >
                  <option value="admin">Admin</option>
                  <option value="practitioner">Practitioner</option>
                  <option value="staff">Staff</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddMemberModal(false);
                    setMemberFormData({ user_id: 0, role: 'practitioner' as OrganisationRole });
                  }}
                  className="px-4 py-2 border border-border rounded-md text-sm font-medium text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Add Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
