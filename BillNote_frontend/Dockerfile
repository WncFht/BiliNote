FROM node:20-bullseye AS builder

WORKDIR /app

COPY ./BillNote_frontend/package.json ./BillNote_frontend/package-lock.json ./
RUN npm ci

COPY ./BillNote_frontend/ ./
ENV DOCKER_BUILD=1 \
    NODE_OPTIONS=--max-old-space-size=2048
RUN npm run build

FROM nginx:1.25-alpine

RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./BillNote_frontend/deploy/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
