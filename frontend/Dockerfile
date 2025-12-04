# Dewey Frontend Dockerfile
FROM node:20-alpine as base

WORKDIR /app

# Development stage
FROM base as development

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start dev server
CMD ["npm", "run", "dev", "--", "--host"]

# Build stage
FROM base as build

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine as production

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
