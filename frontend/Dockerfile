FROM node:20-alpine AS builder

WORKDIR /app

# Copy package metadata first so dependency installation stays cacheable.
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json ./package-lock.json

RUN npm ci

# Copy the application source after dependency installation.
COPY frontend /app

# Ensure public directory exists for runtime copy, even if repo doesn't include it.
RUN mkdir -p /app/public

RUN npm run build \
	&& npm prune --omit=dev

FROM node:20-alpine AS runtime

ENV NODE_ENV=production \
	NEXT_TELEMETRY_DISABLED=1 \
	PORT=3000

WORKDIR /app

# Run the Next.js server as a non-root user.
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/public /app/public

USER nextjs

EXPOSE 3000

# next start serves the optimized production build.
CMD ["sh", "-c", "npm run start -- --hostname 0.0.0.0 --port ${PORT:-3000}"]
