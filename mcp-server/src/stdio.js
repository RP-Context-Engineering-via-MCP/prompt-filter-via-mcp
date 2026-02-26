#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createMcpServer } from './tools.js';

// Create MCP server with all tools registered
const server = createMcpServer();

// Connect via stdio transport (for Claude Desktop and other LLM clients)
const transport = new StdioServerTransport();
await server.connect(transport);
