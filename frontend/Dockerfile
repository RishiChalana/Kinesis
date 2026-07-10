# KINESIS frontend image — multi-stage: build with Node, serve with nginx.
# Build context: ./frontend

# ---- Stage 1: build the Vite bundle ----
# node:22-alpine (not 18 as in the plan): our Vite 8 / rolldown toolchain uses
# node:util's styleText, added in Node 20.12+ — Node 18 fails at `npm run build`.
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# VITE_API_URL is baked into the bundle at build time (Vite inlines VITE_* vars).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Stage 2: serve the static bundle ----
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
