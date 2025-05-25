# Use Node.js LTS version
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application files
COPY . .

# Set a dummy API key for build time
ENV OPENAI_API_KEY="sk-dummy-key-for-build"

# Build the application
RUN npm run build

# Remove development dependencies
RUN npm prune --production

# Cloud Run will set PORT environment variable
ENV PORT=8080
ENV OPENAI_API_KEY=""

# Expose the port
EXPOSE 8080

# Start the application
CMD ["npm", "start"] 