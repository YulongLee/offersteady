FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_APP_ENV=production
ARG VITE_API_BASE_URL=/
ARG VITE_PUBLIC_APP_VERSION=0.1.0
ENV VITE_APP_ENV=$VITE_APP_ENV
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PUBLIC_APP_VERSION=$VITE_PUBLIC_APP_VERSION

COPY package.json package-lock.json* tsconfig.base.json /app/
COPY apps /app/apps
COPY packages /app/packages

RUN npm install
RUN npm run build -w @offersteady/config
RUN npm run build -w @offersteady/protocol
RUN npm run build -w @offersteady/web

FROM nginx:1.27-alpine AS runtime

COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80
