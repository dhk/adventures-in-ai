import OpenAI from 'openai';

// Configuration validation
if (!process.env.OPENAI_API_KEY) {
  console.warn('Missing OPENAI_API_KEY environment variable');
}

// OpenAI client configuration
export const config = {
  apiKey: process.env.OPENAI_API_KEY || '',
  model: 'gpt-3.5-turbo',
  maxTokens: 500,
  temperature: 0.7,
  systemMessage: 'You are a professional life coach focused on helping people achieve their goals through actionable advice and meaningful insights.'
};

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: config.apiKey,
});

export default openai; 