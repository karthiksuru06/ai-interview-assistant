# Smart AI Interview Assistant: Frontend Dockerfile

# Base: Node 18 Alpine (Lightweight)
FROM node:18-alpine

# Work Directory
WORKDIR /app

# Copy Package Files
COPY package.json package-lock.json ./

# Install Dependencies
RUN npm ci

# Copy Source Code
COPY . .

# Accept API URL as build arg so Vite bakes it into the bundle
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Build production assets
RUN npm run build

# Serve the built app with a simple static server
RUN npm install -g serve

# Expose Port
EXPOSE 5173

# Serve the production build on port 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
