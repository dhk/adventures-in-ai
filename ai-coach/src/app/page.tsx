'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

// Helper function for consistent time formatting
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
};

interface ChatResponse {
  message?: string | { role: string; content: string };
  error?: string;
  details?: unknown;
  usage?: TokenUsage;
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [email, setEmail] = useState('');
  const [isEmailSubmitted, setIsEmailSubmitted] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage>({
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0
  });

  const MAX_QUESTIONS_BEFORE_EMAIL = 10;
  const MAX_QUESTIONS_TOTAL = 30;

  useEffect(() => {
    setIsClient(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    
    if (questionCount >= MAX_QUESTIONS_TOTAL) {
      setError('You have reached the maximum number of questions for this session.');
      return;
    }

    if (questionCount >= MAX_QUESTIONS_BEFORE_EMAIL && !isEmailSubmitted) {
      setError('Please enter your email to continue asking questions.');
      return;
    }

    setLoading(true);
    setError(null);
    
    const newUserMessage: ChatMessage = {
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content: inputMessage.trim()
          }]
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      if (!data.message) {
        throw new Error('No message received from the API');
      }

      if (data.usage) {
        setTokenUsage(prev => ({
          promptTokens: prev.promptTokens + data.usage!.promptTokens,
          completionTokens: prev.completionTokens + data.usage!.completionTokens,
          totalTokens: prev.totalTokens + data.usage!.totalTokens
        }));
      }

      const newAssistantMessage: ChatMessage = {
        role: 'assistant',
        content: typeof data.message === 'string' ? data.message : data.message.content,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, newUserMessage, newAssistantMessage]);
      setQuestionCount(prev => prev + 1);
      setInputMessage('');
    } catch (err: any) {
      console.error('Error sending message:', err);
      setError(err.message || 'An error occurred while sending your message.');
      setLoading(false);
      return;
    }
    
    setLoading(false);
  };

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setIsEmailSubmitted(true);
      setError(null);
    } else {
      setError('Please enter a valid email address.');
    }
  };

  if (!isClient) {
    return (
      <main className="min-h-screen">
        <div className="hero-section bg-gradient-to-br from-primary to-secondary py-3xl">
          <div className="container mx-auto px-md text-center">
            <h1 className="text-5xl font-extrabold text-white mb-lg tracking-tight">
              AI Coach
            </h1>
            <p className="text-lg text-white/90 mb-xl max-w-2xl mx-auto">
              Your networking coach, powered by advanced language models to help you achieve your goals.
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <div className="hero-section bg-gradient-to-br from-primary to-secondary py-12 sm:py-3xl relative overflow-hidden">
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h20v20H0z' fill='%23fff' fill-opacity='.05'/%3E%3C/svg%3E")`
          }}
        />
        
        <div className="container mx-auto px-4 sm:px-md text-center relative z-10">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white mb-4 sm:mb-lg tracking-tight">
            AI Coach
          </h1>
          <p className="text-base sm:text-lg text-white/90 mb-8 sm:mb-xl max-w-2xl mx-auto">
            Your personal AI life coach, powered by advanced language models to help you achieve your goals.
          </p>
          
          <div className="flex items-center justify-center gap-12 text-white/90">
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold mb-1">{tokenUsage.promptTokens}</span>
              <span className="text-xs uppercase tracking-wider opacity-80">Prompt</span>
            </div>
            <div className="h-12 w-px bg-white/20" />
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold mb-1">{tokenUsage.completionTokens}</span>
              <span className="text-xs uppercase tracking-wider opacity-80">Response</span>
            </div>
            <div className="h-12 w-px bg-white/20" />
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold mb-1">{tokenUsage.totalTokens}</span>
              <span className="text-xs uppercase tracking-wider opacity-80">Total</span>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 sm:px-md py-6 sm:py-2xl">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-xl">
          <div className="flex-1 order-2 lg:order-1">
            <div className="card bg-white rounded-xl shadow-lg p-4 sm:p-xl border border-gray-medium/10">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 sm:mb-lg gap-2">
                <h2 className="text-xl sm:text-2xl font-bold text-primary flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Chat with DHK&apos;s AI Coach
                </h2>
                <span className="text-sm bg-primary/10 text-primary px-3 py-1 rounded-full font-medium">
                  {questionCount}/{MAX_QUESTIONS_TOTAL} Questions
                </span>
              </div>

              {questionCount >= MAX_QUESTIONS_BEFORE_EMAIL && !isEmailSubmitted ? (
                <form onSubmit={handleEmailSubmit} className="mb-4 sm:mb-lg w-full">
                  <div className="mb-3 sm:mb-md">
                    <label htmlFor="email" className="block text-sm font-medium text-text-medium mb-2">
                      Enter your email to continue
                    </label>
                    <input
                      type="email"
                      id="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-medium/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                      placeholder="your@email.com"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-accent hover:bg-accent-bright text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Submit Email
                  </button>
                </form>
              ) : (
                <form onSubmit={handleSubmit} className="mb-4 sm:mb-lg">
                  <div className="mb-3 sm:mb-md">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-medium/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none"
                      placeholder="Ask your question..."
                      rows={4}
                      disabled={loading || questionCount >= MAX_QUESTIONS_TOTAL}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading || !inputMessage.trim() || questionCount >= MAX_QUESTIONS_TOTAL}
                    className="w-full bg-accent hover:bg-accent-bright text-white font-semibold py-3 px-4 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Sending...
                      </>
                    ) : 'Send Message'}
                  </button>
                </form>
              )}

              {error && (
                <div className="mb-3 sm:mb-md p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
                  <h3 className="font-semibold mb-1">Error</h3>
                  <p className="text-sm">{error}</p>
                </div>
              )}
            </div>
          </div>

          <div className="w-full lg:w-96 order-1 lg:order-2">
            <div className="card bg-white rounded-xl shadow-lg p-4 sm:p-xl sticky top-4 border border-gray-medium/10">
              <h2 className="text-lg sm:text-xl font-bold text-primary mb-4 sm:mb-lg flex items-center gap-2">
                <svg className="w-5 h-5 text-primary/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Chat History
              </h2>
              <div className="space-y-3 sm:space-y-md max-h-[400px] lg:max-h-[600px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-medium/50 scrollbar-track-transparent">
                {messages.map((msg, index) => (
                  <div
                    key={`${msg.timestamp}-${index}`}
                    className={`p-4 rounded-lg transition-all ${
                      msg.role === 'user' ? 'bg-gray-light hover:bg-gray-light/80' : 'bg-primary/5 hover:bg-primary/10'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className={`font-semibold text-sm ${msg.role === 'user' ? 'text-primary' : 'text-accent'}`}>
                        {msg.role === 'user' ? 'You' : 'AI Coach'}
                      </span>
                      <span className="text-xs text-text-light bg-white/50 px-2 py-1 rounded-full">
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                    <div className="prose prose-sm max-w-none break-words">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {messages.length === 0 && (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 text-gray-medium/30">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                    </div>
                    <p className="text-text-light text-sm italic">
                      No messages yet. Start the conversation!
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
