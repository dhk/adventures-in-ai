'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  feedback?: 'up' | 'down' | null;
  id: string;
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

  const handleFeedback = (messageId: string, feedback: 'up' | 'down') => {
    setMessages(prevMessages => 
      prevMessages.map(msg => 
        msg.id === messageId 
          ? { ...msg, feedback: msg.feedback === feedback ? null : feedback }
          : msg
      )
    );
    // TODO: Send feedback to backend when we implement authentication
  };

  const createNewMessage = (role: 'user' | 'assistant', content: string): ChatMessage => ({
    role,
    content,
    timestamp: new Date().toISOString(),
    id: Math.random().toString(36).substr(2, 9),
    feedback: null
  });

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
    
    const newUserMessage = createNewMessage('user', inputMessage.trim());

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

      const newAssistantMessage = createNewMessage('assistant', 
        typeof data.message === 'string' ? data.message : data.message.content
      );

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
                    key={msg.id}
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
                    
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-200">
                        <button
                          onClick={() => handleFeedback(msg.id, 'up')}
                          className={`flex items-center gap-2 text-sm transition-colors ${
                            msg.feedback === 'up' 
                              ? 'text-green-600 font-medium' 
                              : 'text-gray-500 hover:text-green-600'
                          }`}
                        >
                          <svg 
                            className={`w-5 h-5 transition-transform ${msg.feedback === 'up' ? 'scale-110' : ''}`} 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path 
                              strokeLinecap="round" 
                              strokeLinejoin="round" 
                              strokeWidth={2} 
                              d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" 
                            />
                          </svg>
                          Helpful
                        </button>
                        <button
                          onClick={() => handleFeedback(msg.id, 'down')}
                          className={`flex items-center gap-2 text-sm transition-colors ${
                            msg.feedback === 'down' 
                              ? 'text-red-600 font-medium' 
                              : 'text-gray-500 hover:text-red-600'
                          }`}
                        >
                          <svg 
                            className={`w-5 h-5 transition-transform ${msg.feedback === 'down' ? 'scale-110' : ''}`} 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path 
                              strokeLinecap="round" 
                              strokeLinejoin="round" 
                              strokeWidth={2} 
                              d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5 0v2a2 2 0 01-2 2h-2.5" 
                            />
                          </svg>
                          Not Helpful
                        </button>
                      </div>
                    )}
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

      {/* Professional Links Footer */}
      <footer className="bg-gray-50 border-t border-gray-100 py-8 mt-auto">
        <div className="container mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-gray-600">
            <a 
              href="https://dhkconsulting.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 hover:text-primary transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              DHK Consulting
            </a>
            <div className="h-4 w-px bg-gray-300 hidden sm:block" />
            <a 
              href="https://dhkondata.substack.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 hover:text-primary transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2" />
              </svg>
              DHK on Data
            </a>
            <div className="h-4 w-px bg-gray-300 hidden sm:block" />
            <a 
              href="https://tidycal.com/davehk/30-minute-coffee" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 hover:text-primary transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Book a Coffee Chat
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
