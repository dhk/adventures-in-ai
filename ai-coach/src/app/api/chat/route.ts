import { NextResponse } from 'next/server';
import openai, { config } from '@/lib/openai';

// Debug log for environment variable
console.log('API Key exists:', !!process.env.OPENAI_API_KEY);

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    if (!config.apiKey) {
      console.error('OpenAI API key is missing');
      return NextResponse.json(
        { error: 'OpenAI API key not configured in environment' },
        { status: 500 }
      );
    }

    // Validate messages format
    if (!Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Invalid messages format' },
        { status: 400 }
      );
    }

    const completion = await openai.chat.completions.create({
      model: config.model,
      messages: [
        {
          role: 'system',
          content: config.systemMessage
        },
        ...messages
      ],
      temperature: config.temperature,
      max_tokens: config.maxTokens,
    });

    return NextResponse.json({
      message: completion.choices[0].message.content
    });

  } catch (error: any) {
    console.error('OpenAI API error:', error);
    return NextResponse.json(
      { 
        error: error?.message || 'An error occurred during your request.',
        details: error?.response?.data || error
      },
      { status: 500 }
    );
  }
} 