FROM node:20-alpine

WORKDIR /app

# Install dependencies first for efficient layer caching
COPY package*.json ./
RUN npm install

# Copy source files
COPY . .

EXPOSE 5173

# Bind to 0.0.0.0 so Vite accepts requests from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
