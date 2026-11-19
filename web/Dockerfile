# syntax=docker/dockerfile:1

FROM node:22-alpine

LABEL org.opencontainers.image.title="Reikun Web" \
      org.opencontainers.image.description="Reikun Web UI" \
      org.opencontainers.image.source="https://github.com/AnkS4/Reikun" \
      org.opencontainers.image.authors="Aniket Satbhai" \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Copy package files (context is the repo root in this build)
COPY web/package*.json ./

# Install dependencies. npm's optional-deps resolution can drop the
# platform-specific rolldown native binding on musl (npm/cli#4828), so install
# it explicitly at the version rolldown declares.
RUN npm ci \
    && npm install --no-save \
       "@rolldown/binding-linux-x64-musl@$(node -p "require('rolldown/package.json').optionalDependencies['@rolldown/binding-linux-x64-musl'] || require('rolldown/package.json').version")"

# Copy source, plus the shared data the SPA imports at build time.
# i18n/ and kana.json sit at / so web's relative '../../../i18n/*.json' and
# '../../../kana.json' imports from both this image and a local repo build
# resolve the same way (sibling of the web root).
COPY web/ ./
COPY i18n/ /i18n/
COPY kana.json /kana.json

# PUBLIC_API_BASE is baked into the static bundle ($app/env/public declares it
# `static: true`) — pass it as a build arg (docker-compose's web service does)
# or the empty value falls back to the schema default in src/env.ts.
ARG PUBLIC_API_BASE=""
ENV PUBLIC_API_BASE="${PUBLIC_API_BASE}"

# Build the app
RUN npm run build

# Expose dev port (5173) for local development with `docker compose run --rm web npm run dev`
EXPOSE 5173

# vite preview writes a temp config bundle under node_modules/.vite-temp, so
# the tree must be writable by the runtime user.
RUN chown -R node:node /app

# Run as the image's built-in unprivileged `node` user (uid 1000), matching the
# backend image's non-root `app` user.
USER node

CMD ["npm", "run", "preview", "--", "--host", "--port", "5173"]