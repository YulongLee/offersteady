FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_ADMIN_API_BASE_URL=/
ARG VITE_PRODUCT_EDITION=global
ARG NPM_REGISTRY=https://registry.npmjs.org/
ENV VITE_ADMIN_API_BASE_URL=$VITE_ADMIN_API_BASE_URL
ENV VITE_PRODUCT_EDITION=$VITE_PRODUCT_EDITION

COPY package.json package-lock.json* tsconfig.base.json /app/
COPY apps/admin/package.json /app/apps/admin/package.json
RUN npm config set registry "$NPM_REGISTRY" && npm install

COPY apps/admin /app/apps/admin
RUN npm run build -w @offersteady/admin

FROM nginx:1.27-alpine AS runtime
COPY infra/nginx/global-admin.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin/dist /usr/share/nginx/html
EXPOSE 80
