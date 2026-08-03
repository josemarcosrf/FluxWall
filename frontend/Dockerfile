# Dockerfile - Frontend (nginx serving React SPA)
# Multi-stage: build React app, then serve with nginx
# Build context: frontend/ (set via Railway rootDirectory)

# ─── Stage 1: Build the React SPA ────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ─── Stage 2: Serve with nginx ───────────────────────────────────
FROM nginx:alpine

# Copy built SPA
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]