FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# Templates under /etc/nginx/templates are envsubst'd into conf.d at startup
# by the base image's entrypoint, which is how $PORT reaches the config.
ENV PORT=80
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
