'use client';

/**
 * Queue Management Page
 *
 * Monitor and manage background job queues for admins.
 */

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api/client';

interface QueueInfo {
  name: string;
  length: number;
  is_empty: boolean;
}

interface WorkerInfo {
  name: string;
  state: string;
  current_job?: string;
  successful_jobs: number;
  failed_jobs: number;
  total_working_time: number;
}

interface QueueStats {
  available: boolean;
  total_queues: number;
  total_workers: number;
  total_jobs: number;
  queues: QueueInfo[];
  workers: WorkerInfo[];
  last_error?: string;
}

interface JobInfo {
  id: string;
  queue: string;
  func_name: string;
  created_at: string;
  enqueued_at: string;
  started_at?: string;
  ended_at?: string;
  result?: string;
  exc_info?: string;
  status: string;
  args: any[];
  kwargs: Record<string, any>;
}

export default function QueueManagementPage() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [failedJobs, setFailedJobs] = useState<JobInfo[]>([]);
  const [selectedQueue, setSelectedQueue] = useState<string | null>(null);
  const [queueJobs, setQueueJobs] = useState<JobInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchStats = async () => {
    try {
      const data = await apiClient.get<QueueStats>('/api/v1/admin/queue/stats');
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchFailedJobs = async () => {
    try {
      const data = await apiClient.get<JobInfo[]>('/api/v1/admin/queue/failed-jobs?limit=20');
      setFailedJobs(data);
    } catch (error) {
      console.error('Failed to fetch failed jobs:', error);
    }
  };

  const fetchQueueJobs = async (queueName: string) => {
    try {
      const data = await apiClient.get<JobInfo[]>(`/api/v1/admin/queue/jobs/${queueName}?limit=50`);
      setQueueJobs(data);
    } catch (error) {
      console.error('Failed to fetch queue jobs:', error);
    }
  };

  const requeueJob = async (jobId: string) => {
    try {
      await apiClient.post(`/api/v1/admin/queue/jobs/${jobId}/requeue`, {});
      await fetchFailedJobs();
      if (selectedQueue) {
        await fetchQueueJobs(selectedQueue);
      }
    } catch (error) {
      console.error('Failed to requeue job:', error);
      alert('Failed to requeue job');
    }
  };

  const cancelJob = async (jobId: string) => {
    try {
      await apiClient.post(`/api/v1/admin/queue/jobs/${jobId}/cancel`, {});
      if (selectedQueue) {
        await fetchQueueJobs(selectedQueue);
      }
    } catch (error) {
      console.error('Failed to cancel job:', error);
      alert('Failed to cancel job');
    }
  };

  const emptyQueue = async (queueName: string) => {
    if (!confirm(`Are you sure you want to empty the ${queueName} queue? This cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.delete(`/api/v1/admin/queue/queues/${queueName}/empty`);
      await fetchStats();
      if (selectedQueue === queueName) {
        setQueueJobs([]);
      }
    } catch (error) {
      console.error('Failed to empty queue:', error);
      alert('Failed to empty queue');
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchStats(), fetchFailedJobs()]);
      setLoading(false);
    };

    loadData();

    // Auto-refresh every 10 seconds if enabled
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchStats();
        fetchFailedJobs();
        if (selectedQueue) {
          fetchQueueJobs(selectedQueue);
        }
      }, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, selectedQueue]);

  useEffect(() => {
    if (selectedQueue) {
      fetchQueueJobs(selectedQueue);
    }
  }, [selectedQueue]);

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading queue stats...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Failed to load queue stats</p>
      </div>
    );
  }

  if (!stats.available) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-card-foreground">Queue Management</h1>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <svg className="w-16 h-16 mx-auto text-yellow-600 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <h2 className="text-xl font-semibold text-yellow-900 mb-2">Queue System Not Available</h2>
          <p className="text-yellow-700 mb-4">{stats.last_error || 'Redis/RQ not installed'}</p>
          <p className="text-sm text-yellow-600">
            Background job processing requires Redis and RQ to be installed and configured.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-card-foreground">Queue Management</h1>
          <p className="text-muted-foreground mt-1">
            Monitor and manage background job queues
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
            Auto-refresh (10s)
          </label>
          <button
            onClick={() => {
              fetchStats();
              fetchFailedJobs();
              if (selectedQueue) fetchQueueJobs(selectedQueue);
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Queues</div>
          <div className="text-2xl font-bold text-card-foreground mt-1">{stats.total_queues}</div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Active Workers</div>
          <div className="text-2xl font-bold text-card-foreground mt-1">{stats.total_workers}</div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Pending Jobs</div>
          <div className="text-2xl font-bold text-card-foreground mt-1">{stats.total_jobs}</div>
        </div>
      </div>

      {/* Queues */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-card-foreground mb-4">Queues</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stats.queues.map((queue) => (
            <div
              key={queue.name}
              className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                selectedQueue === queue.name
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
              onClick={() => setSelectedQueue(queue.name)}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-card-foreground">{queue.name}</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                  queue.length === 0 ? 'bg-green-100 text-green-800' :
                  queue.length < 10 ? 'bg-blue-100 text-blue-800' :
                  queue.length < 50 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {queue.length} jobs
                </span>
              </div>
              {queue.length > 0 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    emptyQueue(queue.name);
                  }}
                  className="text-xs text-red-600 hover:text-red-800"
                >
                  Empty Queue
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Workers */}
      {stats.workers.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-card-foreground mb-4">Workers</h2>
          <div className="space-y-3">
            {stats.workers.map((worker) => (
              <div key={worker.name} className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-card-foreground">{worker.name}</div>
                    {worker.current_job && (
                      <div className="text-sm text-muted-foreground mt-1">
                        Current: {worker.current_job}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`px-2 py-1 text-xs font-medium rounded ${
                      worker.state === 'busy' ? 'bg-blue-100 text-blue-800' :
                      worker.state === 'idle' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {worker.state}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {worker.successful_jobs} successful / {worker.failed_jobs} failed
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDuration(worker.total_working_time)} total
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Queue Jobs Detail */}
      {selectedQueue && (
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-card-foreground mb-4">
            Jobs in {selectedQueue} Queue
          </h2>
          {queueJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Queue is empty
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {queueJobs.map((job) => (
                <div key={job.id} className="border border-border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-mono text-sm text-muted-foreground">{job.id}</div>
                      <div className="font-semibold text-card-foreground mt-1">{job.func_name}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Created: {new Date(job.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {job.status === 'failed' && (
                        <button
                          onClick={() => requeueJob(job.id)}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                          Requeue
                        </button>
                      )}
                      {job.status === 'queued' && (
                        <button
                          onClick={() => cancelJob(job.id)}
                          className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Failed Jobs */}
      {failedJobs.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-card-foreground mb-4">Recent Failed Jobs</h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {failedJobs.map((job) => (
              <div key={job.id} className="border border-destructive/20 bg-destructive/10 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-destructive text-destructive-foreground text-xs font-medium rounded">
                        {job.queue}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">{job.id}</span>
                    </div>
                    <div className="font-semibold text-foreground mt-2">{job.func_name}</div>
                    {job.exc_info && (
                      <div className="text-xs text-foreground mt-2 font-mono bg-muted p-2 rounded border border-border">
                        {job.exc_info}
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground mt-2">
                      Failed: {job.ended_at ? new Date(job.ended_at).toLocaleString() : 'Unknown'}
                    </div>
                  </div>
                  <button
                    onClick={() => requeueJob(job.id)}
                    className="px-3 py-1 bg-primary text-primary-foreground text-sm rounded hover:bg-primary/90 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
