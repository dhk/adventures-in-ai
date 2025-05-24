'use client';

import { useState } from 'react';

interface ChatResponse {
  message?: string;
  error?: string;
  details?: unknown;
}

export default function Home() {
  const [response, setResponse] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testOpenAI = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content: 'Say hello world and confirm you are working!'
            }
          ]
        }),
      });

      const data: ChatResponse = await result.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      setResponse(data.message || '');
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
      console.error('Error testing OpenAI:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <div className="hero-section bg-gradient-to-br from-primary to-secondary py-3xl">
        <div className="container mx-auto px-md text-center">
          <h1 className="text-5xl font-extrabold text-white mb-lg tracking-tight">
            AI Coach
          </h1>
          <p className="text-lg text-white/90 mb-xl max-w-2xl mx-auto">
            Your personal AI life coach, powered by advanced language models to help you achieve your goals.
          </p>
        </div>
      </div>

      <div className="container mx-auto px-md py-2xl">
        <div className="card bg-white rounded-lg shadow-md p-xl max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-primary mb-lg">Test Connection</h2>
          
          <button
            onClick={testOpenAI}
            disabled={loading}
            className="w-full bg-accent hover:bg-accent-bright text-white font-semibold py-md px-lg rounded-md disabled:opacity-50 disabled:cursor-not-allowed mb-md transition-colors duration-200"
          >
            {loading ? 'Testing...' : 'Test OpenAI Connection'}
          </button>

          {error && (
            <div className="mb-md p-md bg-red-100 text-red-700 rounded-md">
              <h3 className="font-semibold mb-xs">Error</h3>
              <p>{error}</p>
            </div>
          )}

          {response && (
            <div className="p-md bg-gray-light rounded-md">
              <h3 className="font-semibold text-primary mb-xs">Response:</h3>
              <p className="whitespace-pre-wrap text-text-dark">{response}</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
