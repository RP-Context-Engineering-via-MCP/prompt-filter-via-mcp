#!/usr/bin/env node
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// CRITICAL: Reroute all standard logging to stderr.
// Claude Desktop communicates via stdout (JSON-RPC). Any plain text logged to stdout will break the connection!
console.log = console.error;
console.warn = console.error;
console.info = console.error;
console.debug = console.error;

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, '../.env') });

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createMcpServer } from './tools.js';

// Create MCP server with all tools registered
const server = createMcpServer();

// Connect via stdio transport (for Claude Desktop and other LLM clients)
const transport = new StdioServerTransport();
await server.connect(transport);
