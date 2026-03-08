import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { randomUUID } from 'crypto';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js';
import { createMcpServer } from './tools.js';

const app = express();
app.use(cors());

// Parse JSON only for the /mcp endpoint (SSE endpoints must not consume the stream)
app.use('/mcp', express.json());

// --- Session stores ---
let transports = new Map();       // SSE sessions
let httpTransports = new Map();   // Streamable HTTP sessions (ChatGPT)

// Root route
app.get('/', (req, res) => {
    res.send('MCP Server is running. Use the Web Client to chat.');
});

// ─────────────────────────────────────────────
// Legacy SSE transport (Claude Desktop / web-client)
// ─────────────────────────────────────────────
app.get('/sse', async (req, res) => {
    console.log("New SSE connection established");
    res.setHeader('X-Accel-Buffering', 'no');
    const transport = new SSEServerTransport("/message", res);
    console.log(`Assigned session ID: ${transport.sessionId}`);

    transports.set(transport.sessionId, transport);

    res.on('close', () => {
        console.log(`Connection closed for session: ${transport.sessionId}`);
        transports.delete(transport.sessionId);
    });

    const mcpServer = createMcpServer();
    await mcpServer.connect(transport);
});

app.post('/message', async (req, res) => {
    const sessionId = req.query.sessionId;
    if (!sessionId) {
        console.error("Missing sessionId in request");
        res.status(400).send("Missing sessionId");
        return;
    }

    const transport = transports.get(sessionId);
    if (!transport) {
        console.error(`Session not found: ${sessionId}`);
        res.status(404).send("Session not found");
        return;
    }

    await transport.handlePostMessage(req, res);
});

// ─────────────────────────────────────────────
// Streamable HTTP transport (ChatGPT)
// POST /mcp  — send messages / initialize session
// GET  /mcp  — open SSE stream for server-to-client events
// DELETE /mcp — close session
// ─────────────────────────────────────────────
app.post('/mcp', async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];

    if (sessionId && httpTransports.has(sessionId)) {
        // Route to existing session
        const transport = httpTransports.get(sessionId);
        await transport.handleRequest(req, res, req.body);
        return;
    }

    if (!sessionId && isInitializeRequest(req.body)) {
        // New session — create transport + MCP server
        const transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: () => randomUUID(),
            onsessioninitialized: (newSessionId) => {
                console.log(`[ChatGPT] New MCP session: ${newSessionId}`);
                httpTransports.set(newSessionId, transport);
            }
        });

        transport.onclose = () => {
            if (transport.sessionId) {
                console.log(`[ChatGPT] Session closed: ${transport.sessionId}`);
                httpTransports.delete(transport.sessionId);
            }
        };

        const mcpServer = createMcpServer();
        await mcpServer.connect(transport);
        await transport.handleRequest(req, res, req.body);
        return;
    }

    res.status(400).json({ error: 'Bad request: missing or invalid session' });
});

app.get('/mcp', async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];
    if (!sessionId || !httpTransports.has(sessionId)) {
        res.status(400).json({ error: 'Invalid or missing session ID' });
        return;
    }
    res.setHeader('X-Accel-Buffering', 'no');
    const transport = httpTransports.get(sessionId);
    await transport.handleRequest(req, res);
});

app.delete('/mcp', async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];
    if (!sessionId || !httpTransports.has(sessionId)) {
        res.status(400).json({ error: 'Invalid or missing session ID' });
        return;
    }
    const transport = httpTransports.get(sessionId);
    await transport.handleRequest(req, res);
    httpTransports.delete(sessionId);
    console.log(`[ChatGPT] Session deleted: ${sessionId}`);
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`MCP Server running on port ${PORT}`);
    console.log(`  SSE transport:              http://localhost:${PORT}/sse`);
    console.log(`  Streamable HTTP transport:  http://localhost:${PORT}/mcp`);
});
