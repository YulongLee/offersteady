FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_APP_ENV=production
ARG VITE_API_BASE_URL=/
ARG VITE_PUBLIC_APP_VERSION=global-production
ARG VITE_GLOBAL_LOCALE=en-US
ARG VITE_GLOBAL_COMMERCE_ENABLED=false
ARG VITE_GLOBAL_COMMERCE_PROVIDER=none
ARG NPM_REGISTRY=https://registry.npmjs.org/
ENV VITE_APP_ENV=$VITE_APP_ENV
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PUBLIC_APP_VERSION=$VITE_PUBLIC_APP_VERSION
ENV VITE_GLOBAL_LOCALE=$VITE_GLOBAL_LOCALE
ENV VITE_GLOBAL_COMMERCE_ENABLED=$VITE_GLOBAL_COMMERCE_ENABLED
ENV VITE_GLOBAL_COMMERCE_PROVIDER=$VITE_GLOBAL_COMMERCE_PROVIDER

COPY package.json package-lock.json* tsconfig.base.json /app/
COPY apps/web-global/package.json /app/apps/web-global/package.json
COPY packages/config/package.json /app/packages/config/package.json
COPY packages/protocol/package.json /app/packages/protocol/package.json
RUN npm config set registry "$NPM_REGISTRY" && npm install

COPY apps/web-global /app/apps/web-global
COPY apps/backend/app/global_desktop_release_manifest.json /app/apps/backend/app/global_desktop_release_manifest.json
COPY ai/prompts/global-screenshot-instruction-v1.txt /app/ai/prompts/global-screenshot-instruction-v1.txt
COPY packages/config /app/packages/config
COPY packages/protocol /app/packages/protocol
RUN npm run build -w @offersteady/config
RUN npm run build -w @offersteady/protocol
RUN npm run build -w @offersteady/web-global

FROM nginx:1.27-alpine AS runtime

COPY infra/nginx/global-web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web-global/dist /usr/share/nginx/html

EXPOSE 80
