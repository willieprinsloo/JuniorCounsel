'use client';

/**
 * Case Q&A Page
 *
 * RAG-powered question answering about case documents.
 */

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { qaAPI } from '@/lib/api/services';
import type { QAResponse } from '@/types/api';

interface QAHistory {
  question: string;
  answer: string;
  sources: QAResponse['sources'];
  confidence: number;
  timestamp: Date;
}

export default function CaseQAPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<QAHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await qaAPI.ask({
        case_id: caseId,
        question: question.trim(),
        limit: 5,
      });

      setHistory((prev) => [
        {
          question: question.trim(),
          answer: response.answer,
          sources: response.sources,
          confidence: response.confidence,
          timestamp: new Date(),
        },
        ...prev,
      ]);

      setQuestion('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ask Questions About Your Case</h1>
          <p className="mt-1 text-sm text-gray-600">
            Get AI-powered answers based on your case documents with source citations.
          </p>
        </div>

        {/* Question Form */}
        <form onSubmit={handleAsk} className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
                Your Question
              </label>
              <textarea
                id="question"
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="e.g., What are the key facts in the plaintiff's founding affidavit?"
                disabled={loading}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Thinking...' : 'Ask Question'}
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

        {/* Q&A History */}
        {history.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-lg font-medium text-gray-900">Conversation History</h2>

            {history.map((item, index) => (
              <div key={index} className="bg-white shadow rounded-lg overflow-hidden">
                {/* Question */}
                <div className="bg-blue-50 px-4 py-3">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-6 w-6 text-blue-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium text-gray-900">{item.question}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {item.timestamp.toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Answer */}
                <div className="px-4 py-4">
                  <div className="flex items-start mb-3">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-6 w-6 text-green-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <div className="ml-3 flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900">Answer</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getConfidenceColor(item.confidence)}`}>
                          {(item.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{item.answer}</p>
                    </div>
                  </div>

                  {/* Sources */}
                  {item.sources.length > 0 && (
                    <div className="mt-4 border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">
                        Sources ({item.sources.length})
                      </h4>
                      <ul className="space-y-3">
                        {item.sources.map((source, sourceIndex) => (
                          <li key={sourceIndex} className="text-sm">
                            <div className="flex items-start">
                              <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-gray-100 text-gray-700 text-xs font-medium flex-shrink-0">
                                {sourceIndex + 1}
                              </span>
                              <div className="ml-3 flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <span className="font-medium text-gray-900">
                                    {source.document_filename}
                                  </span>
                                  {source.page_number && (
                                    <span className="text-gray-500">
                                      Page {source.page_number}
                                    </span>
                                  )}
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                                    {(source.similarity * 100).toFixed(1)}% match
                                  </span>
                                </div>
                                <p className="text-gray-600">{source.content}</p>
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {history.length === 0 && !loading && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-600">
              Ask a question to get started. Your answers will appear here with source citations.
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
