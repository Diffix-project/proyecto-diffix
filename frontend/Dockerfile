FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Variables que Vite hornea en el bundle (build-time). Llegan como build args
# desde docker-compose.yml. La publishable key de Clerk es pública.
ARG VITE_CLERK_PUBLISHABLE_KEY
ARG VITE_API_BASE_URL
ENV VITE_CLERK_PUBLISHABLE_KEY=${VITE_CLERK_PUBLISHABLE_KEY}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# Servir el build con vite preview para desarrollo.
# Para producción reemplazar esta etapa por nginx.
FROM node:20-alpine AS production

WORKDIR /app

COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/vite.config.ts ./vite.config.ts

EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
