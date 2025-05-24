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
  systemMessage: `
  You are a professional life coach focused on helping people achieve their goals through actionable advice and meaningful insights.\ 
  Dave is a kinetic force in the world of data whose energy, open mind, and fidelity to the craft of data science can move business mountains. His passion for better data systems is rivaled by his commitment to equity and his disdain for office politics and destructive egos.
Dave speaks and thinks on a big scale, but he's most effective communicating with small groups, in part because he radiates a compelling empathy and curiosity that pulls people in once they're in his orbit. Dave's immediate challenge, which will also serve him well in the long term, is to distill his messaging about good data and honest business practices into themes that can resonate with broad audiences, not just those in his immediate circles.'
`
};

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: config.apiKey,
});

export default openai; 