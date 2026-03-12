'use client';

/**
 * Case Search Page
 *
 * Vector-based semantic search within a case's documents.
 */

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { searchAPI } from '@/lib/api/services';
import type { SearchResult } from '@/types/api';

export default function CaseSearchPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');

  const [filters, setFilters] = useState({
    document_type: '',
    limit: 10,
    similarity_threshold: 0.7,
  });

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    setError('');
    setSearched(true);

    try {
      const response = await searchAPI.search({
        case_id: caseId,
        query: query.trim(),
        limit: filters.limit,
        similarity_threshold: filters.similarity_threshold,
        document_type: filters.document_type || undefined,
      });

      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Search Case Documents</h1>
          <p className="mt-1 text-sm text-gray-600">
            Use semantic search to find relevant excerpts from your case documents.
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Search Query
              </label>
              <input
                type="text"
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="e.g., What evidence supports the plaintiff's claim?"
                disabled={searching}
              />
            </div>

            {/* Filters */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="document_type" className="block text-sm font-medium text-gray-700">
                  Document Type
                </label>
                <select
                  id="document_type"
                  value={filters.document_type}
                  onChange={(e) => setFilters((prev) => ({ ...prev, document_type: e.target.value }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  disabled={searching}
                >
                  <option value="">All Types</option>
                  <option value="pleading">Pleadings</option>
                  <option value="evidence">Evidence</option>
                  <option value="correspondence">Correspondence</option>
                  <option value="order">Orders</option>
                  <option value="research">Research</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label htmlFor="limit" className="block text-sm font-medium text-gray-700">
                  Max Results
                </label>
                <select
                  id="limit"
                  value={filters.limit}
                  onChange={(e) => setFilters((prev) => ({ ...prev, limit: Number(e.target.value) }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  disabled={searching}
                >
                  <option value="5">5</option>
                  <option value="10">10</option>
                  <option value="20">20</option>
                  <option value="50">50</option>
                </select>
              </div>

              <div>
                <label htmlFor="threshold" className="block text-sm font-medium text-gray-700">
                  Relevance Threshold
                </label>
                <select
                  id="threshold"
                  value={filters.similarity_threshold}
                  onChange={(e) => setFilters((prev) => ({ ...prev, similarity_threshold: Number(e.target.value) }))}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                  disabled={searching}
                >
                  <option value="0.5">50%</option>
                  <option value="0.6">60%</option>
                  <option value="0.7">70%</option>
                  <option value="0.8">80%</option>
                  <option value="0.9">90%</option>
                </select>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={searching || !query.trim()}
                className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {searching ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Results */}
        {searched && !searching && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Search Results ({results.length})
              </h3>

              {results.length === 0 ? (
                <p className="text-sm text-gray-600">
                  No results found. Try adjusting your search query or lowering the relevance threshold.
                </p>
              ) : (
                <ul className="space-y-4">
                  {results.map((result, index) => (
                    <li key={result.chunk_id} className="border-l-4 border-blue-500 pl-4 py-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {(result.similarity * 100).toFixed(1)}% relevant
                            </span>
                            <span className="text-sm font-medium text-gray-900">
                              {result.document_filename}
                            </span>
                            {result.page_number && (
                              <span className="text-sm text-gray-500">
                                Page {result.page_number}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">
                            {result.content}
                          </p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
