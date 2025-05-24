# AI Coach - Next.js Career Coaching Application

An AI-powered career coaching application built with Next.js, TypeScript, and OpenAI.

## Features

- Professional career coaching through AI
- Real-time chat interface with markdown support
- Question limiting and email collection
- Responsive design with Tailwind CSS
- OpenAI integration for intelligent responses

## Prerequisites

- Node.js 18.x or later
- npm or yarn package manager
- OpenAI API key

## Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai-coach
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file in the root directory with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. Run the development server:
```bash
npm run dev
```

## Deployment

### Option 1: Google Cloud Run (Recommended)

Prerequisites:
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- [Docker](https://docs.docker.com/get-docker/) installed
- Google Cloud project created
- Google Cloud billing enabled

1. Initialize Google Cloud SDK and set your project:
```bash
gcloud init
gcloud config set project YOUR_PROJECT_ID
```

2. Enable required APIs:
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

3. Set up environment variables:
```bash
# Set your OpenAI API key as a secret
gcloud secrets create openai-api-key --replication-policy="automatic"
echo -n "your-openai-api-key" | gcloud secrets versions add openai-api-key --data-file=-

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

4. Deploy to Cloud Run:
```bash
# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml \
    --substitutions=_REGION="us-central1",_OPENAI_API_KEY="$(gcloud secrets versions access latest --secret=openai-api-key)"
```

The deployment will:
- Build the container image
- Push it to Google Container Registry
- Deploy to Cloud Run
- Set up HTTPS automatically
- Configure environment variables

Your application will be available at the URL provided by Cloud Run after deployment.

### Monitoring and Scaling

Cloud Run automatically provides:
- Auto-scaling based on traffic
- Zero cost when not in use
- Request-based pricing
- Automatic HTTPS
- Global load balancing

Monitor your application:
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-coach"

# View service details
gcloud run services describe ai-coach
```

### Cost Optimization

Cloud Run charges based on:
- Number of requests
- Time spent processing requests
- Memory allocated

Tips for cost optimization:
1. Set appropriate memory limits
2. Use cold start optimization techniques
3. Implement caching where possible
4. Monitor and adjust concurrency settings

### Option 2: Vercel (Recommended)

1. Push your code to a GitHub repository
2. Visit [Vercel](https://vercel.com) and import your repository
3. Add your `OPENAI_API_KEY` in the Environment Variables section
4. Deploy!

### Option 3: Traditional Server

1. Build the application:
```bash
npm run build
```

2. Set up environment variables on your server:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

3. Start the production server:
```bash
npm start
```

### Option 4: Docker Deployment

1. Build the Docker image:
```bash
docker build -t ai-coach .
```

2. Run the container:
```bash
docker run -p 3000:3000 -e OPENAI_API_KEY=your_key_here ai-coach
```

## Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key
- `PORT` (optional): Server port (default: 3000)
- `NODE_ENV` (optional): Environment mode (development/production)

## Security Considerations

1. Never commit your `.env` files to version control
2. Use environment variables for sensitive data
3. Implement rate limiting in production
4. Set up proper CORS policies
5. Use HTTPS in production

## Production Best Practices

1. Enable caching where appropriate
2. Implement error tracking (e.g., Sentry)
3. Set up monitoring and logging
4. Configure proper security headers
5. Optimize bundle size

## License

[Your chosen license]

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
