# Stage 1: Build Frontend SPA
FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Caddy Web Server
FROM caddy:2.8.4-alpine
COPY --from=frontend-builder /app/dist /usr/share/caddy
COPY docker/caddy/Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
