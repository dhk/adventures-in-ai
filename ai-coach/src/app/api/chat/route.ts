import OpenAI from 'openai';
import { NextResponse } from 'next/server';

// Debug log for environment variable
console.log('API Key exists:', !!process.env.OPENAI_API_KEY);

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY || '',  // Provide empty string as fallback
});

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    if (!process.env.OPENAI_API_KEY) {
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
      model: 'gpt-3.5-turbo',  // Using a more widely available model
      messages: [
        {
          role: 'system',
          content: 'You are a professional life coach focused on helping people achieve their goals through actionable advice and meaningful insights.'
        },
        ...messages
      ],
      temperature: 0.7,
      max_tokens: 500,
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