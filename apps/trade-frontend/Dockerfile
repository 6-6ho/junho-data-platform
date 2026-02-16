# Build stage
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
# Use npm install instead of npm ci to handle lockfile mismatch
RUN npm install
COPY . .
# Execute typescript and vite directly via node
RUN node ./node_modules/typescript/bin/tsc -b && node ./node_modules/vite/bin/vite.js build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
