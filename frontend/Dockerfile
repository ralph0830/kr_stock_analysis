# Frontend Dockerfile (Next.js 14)
# Build context: project root

# Base stage
FROM node:20-alpine AS base
WORKDIR /app

# Dependencies stage
FROM base AS deps
RUN apk add --no-cache libc6-compat curl
COPY frontend/package*.json ./
RUN npm install
ENV PATH="/app/node_modules/.bin:${PATH}"

# Development stage - with hot reload
FROM base AS development
ENV NODE_ENV=development
ENV PATH="/app/node_modules/.bin:${PATH}"
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./frontend/
WORKDIR /app/frontend
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production stage (build required)
FROM base AS build
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm run build

# Production runner
FROM base AS production
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=build /app/frontend/public ./public
RUN mkdir -p /app/.next/standalone
COPY --from=build /app/frontend/.next/standalone ./
COPY --from=build /app/frontend/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
