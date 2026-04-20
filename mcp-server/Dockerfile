# Use a lightweight Node.js Alpine image
FROM node:20.12-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Expose the MCP server port
EXPOSE 3001

# Command to run the application
CMD ["npm", "start"]
