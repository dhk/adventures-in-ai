import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { rateLimit, getRateLimitHeaders, createRateLimitResponse } from '@/lib/rateLimit';

// Rate limit configuration
const RATE_LIMIT_CONFIG = {
  tokensPerInterval: 20,    // 20 requests
  interval: 3600 * 1000,    // per hour (in milliseconds)
};

export async function POST(req: NextRequest) {
  try {
    // Initialize OpenAI client with runtime environment variable
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });

    const body = await req.json();
    const { messages } = body;

    // Log request details
    console.log('Chat API Request:', {
      timestamp: new Date().toISOString(),
      apiKeyExists: Boolean(process.env.OPENAI_API_KEY),
      apiKeyPrefix: process.env.OPENAI_API_KEY?.slice(0, 5) || 'none',
      userQuestion: messages?.[messages.length - 1]?.content || 'no question found',
      totalMessages: messages?.length || 0
    });

    if (!messages) {
      console.error('Chat API Error: No messages provided');
      return new NextResponse(
        JSON.stringify({ error: 'Messages are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    try {
      const completion = await openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages,
        temperature: 0.7,
        max_tokens: 500,
      });

      // Log successful completion
      console.log('Chat API Success:', {
        timestamp: new Date().toISOString(),
        promptTokens: completion.usage?.prompt_tokens,
        completionTokens: completion.usage?.completion_tokens,
        totalTokens: completion.usage?.total_tokens,
        messageLength: completion.choices[0].message.content.length
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

    } catch (openaiError: any) {
      // Log OpenAI-specific errors
      console.error('OpenAI API Error:', {
        timestamp: new Date().toISOString(),
        error: openaiError.message,
        code: openaiError.code,
        type: openaiError.type,
        param: openaiError.param,
        statusCode: openaiError.status
      });
      throw openaiError;
    }

  } catch (error: any) {
    console.error('Chat API Error:', {
      timestamp: new Date().toISOString(),
      error: error.message,
      stack: error.stack,
      type: error.constructor.name
    });
    
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