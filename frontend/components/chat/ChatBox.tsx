'use client';

/**
 * Professional ChatBox Component
 *
 * Modern chat interface inspired by ChatGPT, Claude, and TalkJS.
 * Features:
 * - Clean chat bubble design
 * - Auto-scrolling
 * - Typing indicators
 * - Markdown support
 * - Source citations
 * - Auto-growing input
 */

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  sources?: Array<{
    id?: string;
    document_filename: string;
    page_number?: number;
    similarity?: number;
    content?: string;
  }>;
  confidence?: number;
  toolsUsed?: string[];  // Names of tools that were called
  toolResults?: Array<{
    tool: string;
    result: any;
  }>;
}

interface ChatBoxProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  placeholder?: string;
  welcomeMessage?: string;
  className?: string;
  showTimestamps?: boolean;
  enableMarkdown?: boolean;
  maxHeight?: string;
}

export function ChatBox({
  messages,
  onSendMessage,
  isLoading = false,
  placeholder = 'Type your message...',
  welcomeMessage,
  className = '',
  showTimestamps = true,
  enableMarkdown = true,
  maxHeight = '600px',
}: ChatBoxProps) {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending || isLoading) return;

    const message = input.trim();
    setInput('');
    setIsSending(true);

    try {
      await onSendMessage(message);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Restore input on error
      setInput(message);
    } finally {
      setIsSending(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const displayMessages = welcomeMessage && messages.length === 0
    ? [{ id: 'welcome', role: 'system' as const, content: welcomeMessage, timestamp: new Date() }]
    : messages;

  return (
    <div className={`flex flex-col bg-background rounded-lg border border-border shadow-sm ${maxHeight === '100%' ? 'h-full' : ''} ${className}`}>
      {/* Messages Container */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-2"
        style={maxHeight !== '100%' ? { maxHeight } : {}}
      >
        <div className="flex flex-col justify-end min-h-full space-y-2">
        {displayMessages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}
          >
            <div
              className={`flex gap-2 ${message.role === 'user' ? 'max-w-[75%] flex-row-reverse' : 'max-w-[98%] flex-row'}`}
            >
              {/* Avatar */}
              <div className="flex-shrink-0">
                {message.role === 'user' ? (
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center border-2 border-primary/20">
                    <svg className="h-5 w-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                ) : (
                  <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center border-2 border-primary/20">
                    <svg className="h-5 w-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                )}
              </div>

              {/* Message Bubble */}
              <div className="flex flex-col gap-1">
                <div
                  className={`rounded-2xl px-3 py-2 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : message.role === 'system'
                      ? 'bg-muted/50 text-muted-foreground border border-border'
                      : 'bg-card text-card-foreground border border-border'
                  }`}
                >
                  {enableMarkdown && message.role !== 'user' ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">
                      {message.content}
                    </p>
                  )}

                  {/* Tool Usage Indicator with Results */}
                  {message.toolsUsed && message.toolsUsed.length > 0 && message.role === 'assistant' && (
                    <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                      <div className="flex flex-wrap gap-2">
                        <span className="text-xs font-medium text-muted-foreground">🔧 Tools used:</span>
                        {message.toolsUsed.map((tool, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                          >
                            {tool === 'search_case_documents' && '🔍 Document Search'}
                            {tool === 'get_research_summary' && '📋 Research Summary'}
                            {!['search_case_documents', 'get_research_summary'].includes(tool) && tool}
                          </span>
                        ))}
                      </div>

                      {/* Tool Results Details */}
                      {message.toolResults && message.toolResults.map((toolResult, idx) => (
                        <div key={idx} className="bg-muted/30 rounded-lg p-3 text-xs space-y-2">
                          {toolResult.tool === 'search_case_documents' && Array.isArray(toolResult.result) && (
                            <>
                              <div className="font-medium text-foreground flex items-center gap-2">
                                <span>🔍 Found {toolResult.result.length} relevant document(s)</span>
                              </div>
                              <div className="space-y-1.5">
                                {toolResult.result.map((doc: any, docIdx: number) => (
                                  <div key={docIdx} className="bg-background/50 rounded p-2 border border-border/30">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-primary/10 text-primary text-[10px] font-medium">
                                        {docIdx + 1}
                                      </span>
                                      <span className="font-medium text-foreground">{doc.document}</span>
                                      {doc.page && <span className="text-muted-foreground">• Page {doc.page}</span>}
                                    </div>
                                    {doc.content && (
                                      <p className="text-muted-foreground line-clamp-2 ml-6">{doc.content}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </>
                          )}
                          {toolResult.tool === 'get_research_summary' && (
                            <div className="font-medium text-foreground">
                              📋 Retrieved case research summary
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Confidence Badge */}
                  {message.confidence !== undefined && message.role === 'assistant' && (
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          message.confidence >= 0.8
                            ? 'bg-success/10 text-success'
                            : message.confidence >= 0.6
                            ? 'bg-secondary/10 text-secondary'
                            : 'bg-destructive/10 text-destructive'
                        }`}
                      >
                        {(message.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                  )}
                </div>

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className="px-2 space-y-1.5">
                    <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                    {message.sources.map((source, idx) => (
                      <div
                        key={idx}
                        className="text-xs text-muted-foreground bg-muted/30 rounded-lg px-2.5 py-1.5 border border-border/50"
                      >
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-primary/10 text-primary text-[10px] font-medium">
                            {idx + 1}
                          </span>
                          <span className="font-medium text-foreground">
                            {source.document_filename}
                          </span>
                          {source.page_number && (
                            <span className="text-muted-foreground">• p. {source.page_number}</span>
                          )}
                          {source.similarity && (
                            <span className="ml-auto text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                              {(source.similarity * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        {source.content && (
                          <p className="text-muted-foreground line-clamp-2">{source.content}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Timestamp */}
                {showTimestamps && (
                  <p className="text-xs text-muted-foreground px-2">
                    {formatTime(message.timestamp)}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex gap-2 max-w-[98%]">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center border-2 border-primary/20">
                <svg className="h-5 w-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div className="bg-card border border-border rounded-2xl px-4 py-3">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                      <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-xs text-muted-foreground">Thinking...</span>
                  </div>
                  <p className="text-xs text-muted-foreground italic">
                    AI is analyzing your request and may search case documents...
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card/50 p-2">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isSending || isLoading}
              rows={1}
              className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none transition-all disabled:opacity-50 pr-12"
              style={{ minHeight: '48px', maxHeight: '150px' }}
            />
            <div className="absolute bottom-3 right-3 text-xs text-muted-foreground">
              {input.length > 0 && `${input.length}/1000`}
            </div>
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isSending || isLoading}
            className="flex-shrink-0 h-12 w-12 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center group"
          >
            <svg
              className="h-5 w-5 transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Press <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted rounded border border-border">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted rounded border border-border">Shift</kbd> + <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted rounded border border-border">Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}
