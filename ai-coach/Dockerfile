# Use Node.js LTS version
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies)
RUN npm ci

# Copy application files
COPY . .

# Build the application
RUN npm run build

# Remove development dependencies after build
RUN npm prune --production

# Cloud Run will set PORT environment variable
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Start the application
CMD ["npm", "start"] 