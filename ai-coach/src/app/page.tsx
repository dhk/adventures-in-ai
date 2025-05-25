'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// Helper function for consistent time formatting
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
};

interface ChatResponse {
  message?: string;
  error?: string;
  details?: unknown;
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
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: [newUserMessage] }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      const newAssistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message || '',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, newUserMessage, newAssistantMessage]);
      setQuestionCount(prev => prev + 1);
      setInputMessage('');
    } catch (err: any) {
      setError(err.message || 'An error occurred while sending your message.');
      console.error('Error sending message:', err);
    } finally {
      setLoading(false);
    }
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
      <div className="hero-section bg-gradient-to-br from-primary to-secondary py-12 sm:py-3xl">
        <div className="container mx-auto px-4 sm:px-md text-center">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white mb-4 sm:mb-lg tracking-tight">
            AI Coach
          </h1>
          <p className="text-base sm:text-lg text-white/90 mb-6 sm:mb-xl max-w-2xl mx-auto">
            Your personal AI life coach, powered by advanced language models to help you achieve your goals.
          </p>
        </div>
      </div>

      <div className="container mx-auto px-4 sm:px-md py-6 sm:py-2xl">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-xl">
          {/* Chat Interface */}
          <div className="flex-1 order-2 lg:order-1">
            <div className="card bg-white rounded-lg shadow-md p-4 sm:p-xl">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 sm:mb-lg gap-2">
                <h2 className="text-xl sm:text-2xl font-bold text-primary">Chat with DHK's AI Coach</h2>
                <span className="text-sm text-text-medium">
                  Questions: {questionCount}/{MAX_QUESTIONS_TOTAL}
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
                      className="w-full px-3 py-2 sm:px-md sm:py-sm border border-gray-medium rounded-md"
                      placeholder="your@email.com"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-accent hover:bg-accent-bright text-white font-semibold py-3 sm:py-md px-4 sm:px-lg rounded-md transition-colors duration-200"
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
                      className="w-full px-3 py-2 sm:px-md sm:py-sm border border-gray-medium rounded-md"
                      placeholder="Ask your question..."
                      rows={4}
                      disabled={loading || questionCount >= MAX_QUESTIONS_TOTAL}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading || !inputMessage.trim() || questionCount >= MAX_QUESTIONS_TOTAL}
                    className="w-full bg-accent hover:bg-accent-bright text-white font-semibold py-3 sm:py-md px-4 sm:px-lg rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    {loading ? 'Sending...' : 'Send Message'}
                  </button>
                </form>
              )}

              {error && (
                <div className="mb-3 sm:mb-md p-3 sm:p-md bg-red-100 text-red-700 rounded-md">
                  <h3 className="font-semibold mb-1 sm:mb-xs">Error</h3>
                  <p>{error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Chat History */}
          <div className="w-full lg:w-96 order-1 lg:order-2">
            <div className="card bg-white rounded-lg shadow-md p-4 sm:p-xl sticky top-4">
              <h2 className="text-lg sm:text-xl font-bold text-primary mb-4 sm:mb-lg">Chat History</h2>
              <div className="space-y-3 sm:space-y-md max-h-[400px] lg:max-h-[600px] overflow-y-auto">
                {messages.map((msg, index) => (
                  <div
                    key={`${msg.timestamp}-${index}`}
                    className={`p-3 sm:p-md rounded-md ${
                      msg.role === 'user' ? 'bg-gray-light' : 'bg-primary/5'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1 sm:mb-xs">
                      <span className="font-semibold text-sm text-text-medium">
                        {msg.role === 'user' ? 'You' : 'AI Coach'}
                      </span>
                      <span className="text-xs text-text-light">
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                    <div className="prose prose-sm max-w-none break-words">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {messages.length === 0 && (
                  <p className="text-text-light text-center italic text-sm">
                    No messages yet. Start the conversation!
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
