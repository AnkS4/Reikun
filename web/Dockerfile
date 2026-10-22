# syntax=docker/dockerfile:1

FROM node:22-alpine

LABEL org.opencontainers.image.title="Reikun Web" \
      org.opencontainers.image.description="Reikun Web UI" \
      org.opencontainers.image.source="https://github.com/AnkS4/Reikun" \
      org.opencontainers.image.authors="Aniket Satbhai" \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build the app
RUN npm run build

# Expose dev port (5173) for local development with `docker compose run --rm web npm run dev`
EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "--port", "5173"]