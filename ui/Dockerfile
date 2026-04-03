# UI image (Nuxt 4 production build).
# Build from repository root: docker build -f ui/Dockerfile .
FROM node:22-slim AS build

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.source="https://github.com/chatondearu/cool-tts-service" \
      org.opencontainers.image.title="cool-tts-service-ui" \
      org.opencontainers.image.version="${APP_VERSION}"

WORKDIR /app

COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY VERSION /tmp/VERSION
COPY ui/ .

RUN export NUXT_PUBLIC_APP_VERSION="$(tr -d '\n\r' </tmp/VERSION)" \
    && npm run build

FROM node:22-slim

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.source="https://github.com/chatondearu/cool-tts-service" \
      org.opencontainers.image.title="cool-tts-service-ui" \
      org.opencontainers.image.version="${APP_VERSION}"

WORKDIR /app

COPY --from=build /app/.output /app/.output

ENV HOST=0.0.0.0
ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
