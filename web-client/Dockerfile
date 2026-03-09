# Use a lightweight Node.js Alpine image
FROM node:20.12-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose the Vite dev server port
EXPOSE 3009

# Run the dev server on port 3009, making it accessible from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3009"]
