'use client';

/**
 * Case Q&A Page
 *
 * RAG-powered question answering about case documents with persistent chat history.
 */

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { qaAPI, chatSessionsAPI } from '@/lib/api/services';
import type { QAResponse, ChatMessage, ChatSession } from '@/types/api';

interface QAHistory {
  id?: string;
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
  const [loadingSession, setLoadingSession] = useState(true);
  const [error, setError] = useState('');
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Load or create chat session on mount
  useEffect(() => {
    const initializeSession = async () => {
      setLoadingSession(true);
      try {
        // Try to load existing sessions for this case
        const sessionsResponse = await chatSessionsAPI.list({
          case_id: caseId,
          per_page: 10,
        });

        if (sessionsResponse.data.length > 0) {
          // Use the most recent session
          const latestSession = sessionsResponse.data[0];
          setSessions(sessionsResponse.data);
          setCurrentSession(latestSession);

          // Load conversation history from the session
          const sessionDetail = await chatSessionsAPI.get(latestSession.id);
          const loadedHistory: QAHistory[] = sessionDetail.messages.map((msg) => ({
            id: msg.id,
            question: msg.question,
            answer: msg.answer,
            sources: msg.sources || [],
            confidence: msg.confidence,
            timestamp: new Date(msg.created_at),
          })).reverse(); // Reverse to show newest first

          setHistory(loadedHistory);
        } else {
          // Create a new session
          const newSession = await chatSessionsAPI.create({
            case_id: caseId,
            title: `Q&A Session - ${new Date().toLocaleDateString()}`,
          });
          setCurrentSession(newSession);
          setSessions([newSession]);
        }
      } catch (err) {
        console.error('Failed to initialize chat session:', err);
        setError('Failed to load chat history. You can still ask questions.');
      } finally {
        setLoadingSession(false);
      }
    };

    initializeSession();
  }, [caseId]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');

    try {
      // Pass chat session ID to save the message to the backend
      const response = await qaAPI.ask(
        {
          case_id: caseId,
          question: question.trim(),
          limit: 5,
        },
        currentSession?.id // Pass session ID for persistence
      );

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

  // Create a new chat session
  const handleNewSession = async () => {
    try {
      const newSession = await chatSessionsAPI.create({
        case_id: caseId,
        title: `Q&A Session - ${new Date().toLocaleDateString()}`,
      });
      setCurrentSession(newSession);
      setSessions((prev) => [newSession, ...prev]);
      setHistory([]);
      setError('');
    } catch (err) {
      setError('Failed to create new session');
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-success/10 text-success border border-success/20';
    if (confidence >= 0.6) return 'bg-secondary/10 text-secondary border border-secondary/20';
    return 'bg-destructive/10 text-destructive border border-destructive/20';
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Ask Questions About Your Case</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Get AI-powered answers based on your case documents with source citations.
            </p>
          </div>
          {currentSession && (
            <button
              onClick={handleNewSession}
              className="inline-flex items-center px-4 py-2 border border-border rounded-md shadow-sm text-sm font-medium text-card-foreground bg-card hover:bg-muted transition-colors"
            >
              <svg className="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Session
            </button>
          )}
        </div>

        {/* Session Info */}
        {loadingSession ? (
          <div className="bg-card rounded-lg shadow p-4 border border-border">
            <div className="flex items-center">
              <svg className="animate-spin h-5 w-5 text-primary mr-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-sm text-muted-foreground">Loading chat session...</span>
            </div>
          </div>
        ) : currentSession ? (
          <div className="bg-card rounded-lg shadow p-4 border border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <svg className="h-5 w-5 text-primary mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-foreground">{currentSession.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {history.length} message{history.length !== 1 ? 's' : ''} • Session saved automatically
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Question Form */}
        <form onSubmit={handleAsk} className="bg-card shadow rounded-lg p-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="question" className="block text-sm font-medium text-card-foreground mb-2">
                Your Question
              </label>
              <textarea
                id="question"
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="block w-full rounded-md border-input shadow-sm focus:border-primary focus:ring-primary sm:text-sm px-3 py-2 border bg-background text-foreground transition-colors"
                placeholder="e.g., What are the key facts in the plaintiff's founding affidavit?"
                disabled={loading || loadingSession}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={loading || loadingSession || !question.trim()}
                className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Thinking...' : loadingSession ? 'Loading session...' : 'Ask Question'}
              </button>
            </div>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-4 border border-destructive/20">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Q&A History */}
        {history.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-lg font-medium text-foreground">Conversation History</h2>

            {history.map((item, index) => (
              <div key={index} className="bg-card shadow rounded-lg overflow-hidden border border-border">
                {/* Question */}
                <div className="bg-primary/10 px-4 py-3">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-6 w-6 text-primary"
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
                      <p className="text-sm font-medium text-foreground">{item.question}</p>
                      <p className="text-xs text-muted-foreground mt-1">
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
                        className="h-6 w-6 text-success"
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
                        <span className="text-sm font-medium text-foreground">Answer</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getConfidenceColor(item.confidence)}`}>
                          {(item.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <p className="text-sm text-card-foreground whitespace-pre-wrap">{item.answer}</p>
                    </div>
                  </div>

                  {/* Sources */}
                  {item.sources.length > 0 && (
                    <div className="mt-4 border-t border-border pt-4">
                      <h4 className="text-sm font-medium text-foreground mb-3">
                        Sources ({item.sources.length})
                      </h4>
                      <ul className="space-y-3">
                        {item.sources.map((source, sourceIndex) => (
                          <li key={sourceIndex} className="text-sm">
                            <div className="flex items-start">
                              <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-muted text-card-foreground text-xs font-medium flex-shrink-0">
                                {sourceIndex + 1}
                              </span>
                              <div className="ml-3 flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <span className="font-medium text-foreground">
                                    {source.document_filename}
                                  </span>
                                  {source.page_number && (
                                    <span className="text-muted-foreground">
                                      Page {source.page_number}
                                    </span>
                                  )}
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-muted text-card-foreground border border-border">
                                    {(source.similarity * 100).toFixed(1)}% match
                                  </span>
                                </div>
                                <p className="text-muted-foreground">{source.content}</p>
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
          <div className="text-center py-12 bg-card rounded-lg shadow border border-border">
            <svg
              className="mx-auto h-12 w-12 text-muted-foreground"
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
            <p className="mt-2 text-sm text-muted-foreground">
              Ask a question to get started. Your answers will appear here with source citations.
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
