import OpenAI from 'openai';
import prompts from '@/config/prompts';

// Debug environment variables
console.log('Environment Variables:', {
  nodeEnv: process.env.NODE_ENV,
  hasOpenAIKey: Boolean(process.env.OPENAI_API_KEY),
  openAIKeyPrefix: process.env.OPENAI_API_KEY?.slice(0, 5),
  envKeys: Object.keys(process.env).filter(key => key.includes('OPENAI')),
  timestamp: new Date().toISOString()
});

// Configuration validation and logging
const apiKey = process.env.OPENAI_API_KEY;
if (!apiKey) {
  throw new Error('OpenAI API key is required');
}

// OpenAI client configuration
export const config = {
  model: 'gpt-3.5-turbo',
  maxTokens: 500,
  temperature: 0.7,
  systemMessage: prompts.system.coach
};

console.log('OpenAI Configuration:', {
  model: config.model,
  maxTokens: config.maxTokens,
  temperature: config.temperature,
  hasSystemMessage: Boolean(config.systemMessage),
  apiKeyExists: Boolean(config.apiKey)
});

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey,
});

// Validate API key on startup
(async () => {
  try {
    console.log('Validating OpenAI API key...');
    const models = await openai.models.list();
    console.log('✅ OpenAI API key is valid. Available models:', models.data.length);
  } catch (error: any) {
    console.error('❌ OpenAI API key validation failed:', error.message);
    // In production, you might want to throw an error here to prevent the app from starting
    if (process.env.NODE_ENV === 'production') {
      throw error;
    }
  }
})();

export default openai; 