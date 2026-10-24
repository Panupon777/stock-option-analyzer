FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application
COPY . .

ENV BACKEND_URL=http://backend:8000
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js
RUN npm run build

# Expose port
EXPOSE 3000

# Run Next.js
CMD ["npm", "run", "start"]

