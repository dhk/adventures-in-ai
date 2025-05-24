import OpenAI from 'openai';
import prompts from '@/config/prompts';

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
  systemMessage: prompts.system.coach
};

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: config.apiKey,
});

export default openai; 