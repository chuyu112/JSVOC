ARG NODE_IMAGE=node:20-alpine

# ── Build stage ──
FROM ${NODE_IMAGE} AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Production stage ──
FROM ${NODE_IMAGE}
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ARG API_BASE_URL=http://backend:8000
ENV API_BASE_URL=${API_BASE_URL}

# Only production deps + standalone output
COPY package*.json ./
RUN npm ci --omit=dev

# Next.js standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
