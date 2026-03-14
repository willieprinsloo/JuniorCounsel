'use client';

/**
 * Admin Dashboard Page
 *
 * System-wide metrics and health overview.
 */

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';

interface DashboardMetrics {
  total_users: number;
  total_organisations: number;
  total_cases: number;
  total_documents: number;
  total_drafts: number;
  active_organisations: number;
  documents_queued: number;
  documents_processing: number;
  documents_completed: number;
  documents_failed: number;
  drafts_initializing: number;
  drafts_awaiting_intake: number;
  drafts_research: number;
  drafts_drafting: number;
  drafts_review: number;
  drafts_ready: number;
  drafts_failed: number;
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<DashboardMetrics>('/api/v1/admin/dashboard/metrics');
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="mt-2 text-sm text-muted-foreground">Loading dashboard...</p>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md">
        {error || 'Failed to load metrics'}
      </div>
    );
  }

  const StatCard = ({ title, value, subtitle, bgColor }: { title: string; value: number; subtitle?: string; bgColor?: string }) => (
    <div className={`${bgColor || 'bg-card'} border border-border rounded-lg p-6`}>
      <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      <p className="text-3xl font-bold text-card-foreground mt-2">{value.toLocaleString()}</p>
      {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Admin Dashboard</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          System-wide metrics and health overview
        </p>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Users" value={metrics.total_users} />
        <StatCard
          title="Organisations"
          value={metrics.total_organisations}
          subtitle={`${metrics.active_organisations} active`}
        />
        <StatCard title="Total Cases" value={metrics.total_cases} />
        <StatCard title="Total Documents" value={metrics.total_documents} />
      </div>

      {/* Document Processing Stats */}
      <div>
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Document Processing</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Queued"
            value={metrics.documents_queued}
            bgColor="bg-secondary/10"
          />
          <StatCard
            title="Processing"
            value={metrics.documents_processing}
            bgColor="bg-blue-50 dark:bg-blue-900/20"
          />
          <StatCard
            title="Completed"
            value={metrics.documents_completed}
            bgColor="bg-green-50 dark:bg-green-900/20"
          />
          <StatCard
            title="Failed"
            value={metrics.documents_failed}
            bgColor="bg-red-50 dark:bg-red-900/20"
          />
        </div>
      </div>

      {/* Draft Status Stats */}
      <div>
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Draft Sessions</h2>
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Initializing</p>
              <p className="text-2xl font-bold text-card-foreground mt-1">{metrics.drafts_initializing}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Awaiting Intake</p>
              <p className="text-2xl font-bold text-card-foreground mt-1">{metrics.drafts_awaiting_intake}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Research</p>
              <p className="text-2xl font-bold text-card-foreground mt-1">{metrics.drafts_research}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Drafting</p>
              <p className="text-2xl font-bold text-card-foreground mt-1">{metrics.drafts_drafting}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Review</p>
              <p className="text-2xl font-bold text-card-foreground mt-1">{metrics.drafts_review}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Ready</p>
              <p className="text-2xl font-bold text-success mt-1">{metrics.drafts_ready}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Failed</p>
              <p className="text-2xl font-bold text-destructive mt-1">{metrics.drafts_failed}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/admin/users"
            className="block p-6 bg-card border border-border rounded-lg hover:bg-accent transition-colors"
          >
            <h3 className="font-semibold text-card-foreground">Manage Users</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Create, edit, and manage user accounts
            </p>
          </a>
          <a
            href="/admin/organisations"
            className="block p-6 bg-card border border-border rounded-lg hover:bg-accent transition-colors"
          >
            <h3 className="font-semibold text-card-foreground">Manage Organisations</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Configure law firms and chambers
            </p>
          </a>
          <a
            href="/admin/rulebooks"
            className="block p-6 bg-card border border-border rounded-lg hover:bg-accent transition-colors"
          >
            <h3 className="font-semibold text-card-foreground">Manage Rulebooks</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Configure document type rules and templates
            </p>
          </a>
        </div>
      </div>
    </div>
  );
}
