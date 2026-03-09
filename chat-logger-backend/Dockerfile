# Use a lightweight Node.js Alpine image
FROM node:20.12-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Expose the API port
EXPOSE 3005

# Command to run the application
CMD ["npm", "start"]
