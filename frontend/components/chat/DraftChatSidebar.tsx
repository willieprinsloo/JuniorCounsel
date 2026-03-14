'use client';

/**
 * Draft Chat Sidebar Component
 *
 * Professional chat interface for discussing drafts with AI.
 * Appears on right side of draft review screen.
 */

import { useState, useEffect } from 'react';
import { qaAPI } from '@/lib/api/services';
import { ChatBox, ChatMessage } from './ChatBox';

interface DraftChatSidebarProps {
  caseId: string;
  draftId: string;
  draftContent: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DraftChatSidebar({
  caseId,
  draftId,
  draftContent,
  isOpen,
  onClose,
}: DraftChatSidebarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async (message: string) => {
    setLoading(true);

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Call Q&A API with draft context
      const response = await qaAPI.ask({
        case_id: caseId,
        question: `Context: I'm reviewing a draft document (ID: ${draftId}).\n\nDraft excerpt: ${draftContent.substring(0, 500)}...\n\nQuestion: ${message}`,
        limit: 5,
      });

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources?.map((source) => ({
          document_filename: source.document_filename,
          page_number: source.page_number,
          similarity: source.similarity,
          content: source.content,
        })),
        confidence: response.confidence,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const quickActions = [
    {
      label: 'Review section',
      message: 'Review the current section for legal accuracy and completeness',
    },
    {
      label: 'Strengthen argument',
      message: 'Suggest ways to strengthen the legal arguments in this draft',
    },
    {
      label: 'Verify citations',
      message: 'Check if all citations are properly supported by the case documents',
    },
    {
      label: 'Grammar check',
      message: 'Check the draft for grammar, spelling, and formatting issues',
    },
  ];

  return (
    <div className="fixed right-0 top-0 h-screen w-96 bg-background border-l border-border shadow-2xl flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card">
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center border-2 border-primary/20">
            <svg className="h-5 w-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-foreground">Draft Assistant</h2>
            <p className="text-xs text-muted-foreground">AI-powered legal assistant</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-accent"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Chat Container */}
      <div className="flex-1 flex flex-col min-h-0">
        <ChatBox
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={loading}
          placeholder="Ask about the draft, citations, or legal arguments..."
          welcomeMessage="Hi! I'm your draft assistant. I can help you:\n\n• Review and improve specific sections\n• Check citations and evidence support\n• Suggest stronger legal arguments\n• Answer questions about the draft\n\nWhat would you like to discuss?"
          enableMarkdown={true}
          showTimestamps={false}
          maxHeight="calc(100vh - 280px)"
          className="flex-1"
        />
      </div>

      {/* Quick Actions */}
      <div className="border-t border-border bg-card/50 p-3">
        <p className="text-xs font-medium text-muted-foreground mb-2">Quick Actions:</p>
        <div className="grid grid-cols-2 gap-2">
          {quickActions.map((action, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(action.message)}
              disabled={loading}
              className="text-xs px-3 py-2 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50 transition-colors text-left border border-primary/20"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
