'use client';

/**
 * System Health Monitoring Page
 *
 * Displays comprehensive system health metrics for admins.
 */

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api/client';

interface DatabaseHealth {
  connected: boolean;
  response_time_ms: number;
  active_connections: number;
  total_tables: number;
  last_error?: string;
}

interface RedisHealth {
  available: boolean;
  connected: boolean;
  queue_depths: Record<string, number>;
  worker_count: number;
  last_error?: string;
}

interface SystemResources {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
}

interface RecentActivity {
  documents_uploaded_last_hour: number;
  documents_processed_last_hour: number;
  drafts_created_last_hour: number;
  active_users_last_24h: number;
  failed_jobs_last_hour: number;
}

interface SystemHealth {
  timestamp: string;
  uptime_seconds: number;
  database: DatabaseHealth;
  redis: RedisHealth;
  resources: SystemResources;
  recent_activity: RecentActivity;
}

interface ErrorLogEntry {
  timestamp: string;
  level: string;
  message: string;
  source: string;
  details?: string;
}

export default function HealthMonitoringPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [errors, setErrors] = useState<ErrorLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchHealth = async () => {
    try {
      const data = await apiClient.get<SystemHealth>('/api/v1/admin/health/');
      setHealth(data);
    } catch (error) {
      console.error('Failed to fetch health:', error);
    }
  };

  const fetchErrors = async () => {
    try {
      const data = await apiClient.get<ErrorLogEntry[]>('/api/v1/admin/health/errors?limit=20');
      setErrors(data);
    } catch (error) {
      console.error('Failed to fetch errors:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchHealth(), fetchErrors()]);
      setLoading(false);
    };

    loadData();

    // Auto-refresh every 30 seconds if enabled
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchHealth();
        fetchErrors();
      }, 30000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const getStatusColor = (value: number, thresholds: { warn: number; error: number }): string => {
    if (value >= thresholds.error) return 'text-red-600';
    if (value >= thresholds.warn) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading system health...</p>
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Failed to load system health</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-card-foreground">System Health</h1>
          <p className="text-muted-foreground mt-1">
            Real-time monitoring of system components and resources
          </p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={() => {
              fetchHealth();
              fetchErrors();
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Uptime</div>
          <div className="text-2xl font-bold text-card-foreground mt-1">
            {formatUptime(health.uptime_seconds)}
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Last Updated</div>
          <div className="text-2xl font-bold text-card-foreground mt-1">
            {new Date(health.timestamp).toLocaleTimeString()}
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Overall Status</div>
          <div className="text-2xl font-bold mt-1">
            {health.database.connected && (health.redis.available ? health.redis.connected : true) ? (
              <span className="text-green-600">Healthy</span>
            ) : (
              <span className="text-red-600">Degraded</span>
            )}
          </div>
        </div>
      </div>

      {/* Database Health */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Database</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-muted-foreground">Status</div>
            <div className={`text-lg font-semibold mt-1 ${health.database.connected ? 'text-green-600' : 'text-red-600'}`}>
              {health.database.connected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Response Time</div>
            <div className="text-lg font-semibold mt-1">
              {health.database.response_time_ms.toFixed(1)}ms
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Active Connections</div>
            <div className="text-lg font-semibold mt-1">{health.database.active_connections}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Tables</div>
            <div className="text-lg font-semibold mt-1">{health.database.total_tables}</div>
          </div>
        </div>
        {health.database.last_error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            Error: {health.database.last_error}
          </div>
        )}
      </div>

      {/* Redis/Queue Health */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Redis / Queue System</h2>
        {health.redis.available ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <div className="text-sm text-muted-foreground">Status</div>
                <div className={`text-lg font-semibold mt-1 ${health.redis.connected ? 'text-green-600' : 'text-red-600'}`}>
                  {health.redis.connected ? 'Connected' : 'Disconnected'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Active Workers</div>
                <div className="text-lg font-semibold mt-1">{health.redis.worker_count}</div>
              </div>
            </div>
            {Object.keys(health.redis.queue_depths).length > 0 && (
              <div>
                <div className="text-sm text-muted-foreground mb-2">Queue Depths</div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {Object.entries(health.redis.queue_depths).map(([queue, depth]) => (
                    <div key={queue} className="flex items-center justify-between p-3 bg-muted rounded">
                      <span className="text-sm font-medium">{queue}</span>
                      <span className={`text-lg font-bold ${depth > 100 ? 'text-yellow-600' : depth > 0 ? 'text-blue-600' : 'text-green-600'}`}>
                        {depth >= 0 ? depth : 'Error'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {health.redis.last_error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                Error: {health.redis.last_error}
              </div>
            )}
          </>
        ) : (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded text-yellow-700">
            Redis/RQ not installed. Background job processing unavailable.
          </div>
        )}
      </div>

      {/* System Resources */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">System Resources</h2>
        <div className="space-y-4">
          {/* CPU */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">CPU Usage</span>
              <span className={`text-lg font-semibold ${getStatusColor(health.resources.cpu_percent, { warn: 70, error: 90 })}`}>
                {health.resources.cpu_percent}%
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  health.resources.cpu_percent >= 90 ? 'bg-red-600' :
                  health.resources.cpu_percent >= 70 ? 'bg-yellow-600' : 'bg-green-600'
                }`}
                style={{ width: `${health.resources.cpu_percent}%` }}
              ></div>
            </div>
          </div>

          {/* Memory */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Memory Usage</span>
              <span className={`text-lg font-semibold ${getStatusColor(health.resources.memory_percent, { warn: 80, error: 95 })}`}>
                {health.resources.memory_percent}% ({health.resources.memory_used_mb.toFixed(0)} / {health.resources.memory_total_mb.toFixed(0)} MB)
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  health.resources.memory_percent >= 95 ? 'bg-red-600' :
                  health.resources.memory_percent >= 80 ? 'bg-yellow-600' : 'bg-green-600'
                }`}
                style={{ width: `${health.resources.memory_percent}%` }}
              ></div>
            </div>
          </div>

          {/* Disk */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Disk Usage</span>
              <span className={`text-lg font-semibold ${getStatusColor(health.resources.disk_percent, { warn: 85, error: 95 })}`}>
                {health.resources.disk_percent}% ({health.resources.disk_used_gb.toFixed(1)} / {health.resources.disk_total_gb.toFixed(1)} GB)
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  health.resources.disk_percent >= 95 ? 'bg-red-600' :
                  health.resources.disk_percent >= 85 ? 'bg-yellow-600' : 'bg-green-600'
                }`}
                style={{ width: `${health.resources.disk_percent}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Recent Activity</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{health.recent_activity.documents_uploaded_last_hour}</div>
            <div className="text-sm text-muted-foreground mt-1">Docs Uploaded (1h)</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{health.recent_activity.documents_processed_last_hour}</div>
            <div className="text-sm text-muted-foreground mt-1">Docs Processed (1h)</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">{health.recent_activity.drafts_created_last_hour}</div>
            <div className="text-sm text-muted-foreground mt-1">Drafts Created (1h)</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-indigo-600">{health.recent_activity.active_users_last_24h}</div>
            <div className="text-sm text-muted-foreground mt-1">Active Users (24h)</div>
          </div>
          <div className="text-center">
            <div className={`text-3xl font-bold ${health.recent_activity.failed_jobs_last_hour > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {health.recent_activity.failed_jobs_last_hour}
            </div>
            <div className="text-sm text-muted-foreground mt-1">Failed Jobs (1h)</div>
          </div>
        </div>
      </div>

      {/* Recent Errors */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Recent Errors</h2>
        {errors.length === 0 ? (
          <div className="text-center py-8 text-green-600">
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="font-medium">No recent errors</p>
            <p className="text-sm text-muted-foreground">System is running smoothly</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {errors.map((error, idx) => (
              <div key={idx} className="border border-red-200 bg-red-50 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-red-600 text-white text-xs font-medium rounded">
                        {error.level}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {error.source}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(error.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-red-900 mt-2">
                      {error.message}
                    </div>
                    {error.details && (
                      <div className="text-xs text-red-700 mt-1 font-mono bg-red-100 p-2 rounded">
                        {error.details}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
