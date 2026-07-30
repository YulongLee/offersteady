FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_ADMIN_API_BASE_URL=/
ENV VITE_ADMIN_API_BASE_URL=$VITE_ADMIN_API_BASE_URL

COPY package.json package-lock.json* tsconfig.base.json /app/
COPY apps/admin /app/apps/admin
RUN npm install
RUN npm run build -w @offersteady/admin

FROM nginx:1.27-alpine AS runtime
COPY infra/nginx/admin.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin/dist /usr/share/nginx/html
EXPOSE 80
