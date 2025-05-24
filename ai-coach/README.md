# AI Coach

A Next.js application that provides AI-powered life coaching using OpenAI's GPT models.

## Setup

1. Clone the repository
2. Install dependencies:
```bash
npm install
```

## Environment Variables

The application requires an OpenAI API key to function. The key should be available in your environment as `OPENAI_API_KEY`. 

There are two ways to provide this:
1. Set it in your shell environment (recommended for development)
2. Create a `.env.local` file with the key (for deployment)

## Project Structure

```
src/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   │   └── chat/         # OpenAI chat endpoint
│   │   └── layout.tsx    # Root layout
│   └── layout.tsx        # Root layout
└── lib/                   # Shared libraries
    └── openai.ts         # OpenAI configuration and client
```

## OpenAI Integration

The OpenAI integration is configured in `src/lib/openai.ts`. Key configuration options:

- Model: gpt-3.5-turbo
- Max Tokens: 500
- Temperature: 0.7

The system message sets the AI to act as a professional life coach.

### API Endpoints

#### POST /api/chat

Accepts chat messages and returns AI responses.

Request body:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Your message here"
    }
  ]
}
```

Response:
```json
{
  "message": "AI response here"
}
```

Error Response:
```json
{
  "error": "Error message",
  "details": "Additional error details"
}
```

## Development

Run the development server:

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
