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
import { ChatBox, ChatMessage as ChatBoxMessage } from '@/components/chat/ChatBox';
import type { QAResponse, ChatMessage, ChatSession } from '@/types/api';

export default function CaseQAPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [messages, setMessages] = useState<ChatBoxMessage[]>([]);
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
          const loadedMessages: ChatBoxMessage[] = sessionDetail.messages.flatMap((msg) => [
            {
              id: `${msg.id}-question`,
              role: 'user' as const,
              content: msg.question,
              timestamp: new Date(msg.created_at),
            },
            {
              id: `${msg.id}-answer`,
              role: 'assistant' as const,
              content: msg.answer,
              timestamp: new Date(msg.created_at),
              sources: msg.sources || [],
              confidence: msg.confidence,
            },
          ]);

          setMessages(loadedMessages);
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

  const handleSendMessage = async (message: string) => {
    setLoading(true);
    setError('');

    // Add user message immediately
    const userMessage: ChatBoxMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Pass chat session ID to save the message to the backend
      const response = await qaAPI.ask(
        {
          case_id: caseId,
          question: message,
          limit: 5,
        },
        currentSession?.id // Pass session ID for persistence
      );

      // Add assistant response
      const assistantMessage: ChatBoxMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        confidence: response.confidence,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer');
      // Add error message
      const errorMessage: ChatBoxMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your question. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
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
      setMessages([]);
      setError('');
    } catch (err) {
      setError('Failed to create new session');
    }
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
                    {messages.length} message{messages.length !== 1 ? 's' : ''} • Session saved automatically
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-4 border border-destructive/20">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Professional Chat Interface */}
        <ChatBox
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={loading}
          placeholder="Ask a question about your case documents..."
          welcomeMessage="Hi! I'm your AI legal assistant. I can help you find information in your case documents and answer questions about your case. What would you like to know?"
          enableMarkdown={true}
          showTimestamps={true}
          maxHeight="600px"
        />
      </div>
    </AppLayout>
  );
}
