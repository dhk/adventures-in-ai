import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { rateLimit, getRateLimitHeaders, createRateLimitResponse } from '@/lib/rateLimit';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Rate limit configuration
const RATE_LIMIT_CONFIG = {
  tokensPerInterval: 20,    // 20 requests
  interval: 3600 * 1000,    // per hour (in milliseconds)
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages } = body;

    if (!messages) {
      return new NextResponse(
        JSON.stringify({ error: 'Messages are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages,
      temperature: 0.7,
      max_tokens: 500,
    });

    // Extract token usage from the response
    const usage = {
      promptTokens: completion.usage?.prompt_tokens || 0,
      completionTokens: completion.usage?.completion_tokens || 0,
      totalTokens: completion.usage?.total_tokens || 0,
    };

    return new NextResponse(
      JSON.stringify({ 
        message: completion.choices[0].message,
        usage 
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );

  } catch (error: any) {
    console.error('Error in chat API:', error);
    
    return new NextResponse(
      JSON.stringify({
        error: 'Internal Server Error',
        details: error.message
      }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
} 