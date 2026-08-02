# Dockerfile - FluxWall frontend (React/Vite → nginx)
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Build the SPA
COPY . .
RUN npm run build

# ─── Runtime: serve static build with nginx ───────────────────
FROM nginx:1.27-alpine

# SPA fallback: serve index.html for client-side routes.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]