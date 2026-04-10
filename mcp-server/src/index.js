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

// ─────────────────────────────────────────────
// Request / Response logger
// ─────────────────────────────────────────────
app.use((req, res, next) => {
    const start = Date.now();
    const via = req.headers['x-forwarded-for'] ? '🌐 ngrok' : '🏠 local';

    // Capture response body for logging
    const originalJson = res.json.bind(res);
    const originalSend = res.send.bind(res);
    let responseBody;

    res.json = (body) => { responseBody = body; return originalJson(body); };
    res.send = (body) => { responseBody = body; return originalSend(body); };

    res.on('finish', () => {
        const ms = Date.now() - start;
        const statusIcon = res.statusCode < 300 ? '✅' : res.statusCode < 400 ? '↩️' : '❌';
        const bodyPreview = responseBody
            ? JSON.stringify(responseBody).slice(0, 80)
            : '';
        console.log(
            `${statusIcon} [${new Date().toISOString()}] ${via} | ${req.method} ${req.path} → ${res.statusCode} (${ms}ms)` +
            (bodyPreview ? ` | resp: ${bodyPreview}...` : '')
        );
    });

    // Log incoming request
    const reqBody = req.body && Object.keys(req.body).length
        ? ` | body: ${JSON.stringify(req.body).slice(0, 80)}...`
        : '';
    console.log(`[${new Date().toISOString()}] ${via} | ${req.method} ${req.path}${reqBody}`);

    next();
});

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

    const clientToken = req.query.token || 
                        (req.headers.authorization ? req.headers.authorization.replace('Bearer ', '') : null) || 
                        req.headers['x-mcp-token'];

    const mcpServer = createMcpServer(clientToken);
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

        const clientToken = req.query.token || 
                            (req.headers.authorization ? req.headers.authorization.replace('Bearer ', '') : null) || 
                            req.headers['x-mcp-token'];

        const mcpServer = createMcpServer(clientToken);
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

const PORT = process.env.PORT || 3001;
const NGROK_URL = 'https://traducianistic-cohen-blowsiest.ngrok-free.dev';

app.listen(PORT, () => {
    const W = 74;
    const line = '═'.repeat(W);
    const pad = (s) => `║  ${s.padEnd(W - 2)}║`;
    console.log('');
    console.log(`╔${line}╗`);
    console.log(pad('MCP SERVER — READY'));
    console.log(`╠${line}╣`);
    console.log(pad('LOCAL ENDPOINTS'));
    console.log(pad(`Health:      http://localhost:${PORT}/`));
    console.log(pad(`SSE:         http://localhost:${PORT}/sse`));
    console.log(pad(`HTTP (MCP):  http://localhost:${PORT}/mcp`));
    console.log(`╠${line}╣`);
    console.log(pad('PUBLIC ENDPOINTS (via ngrok)'));
    console.log(pad(`SSE:         ${NGROK_URL}/sse`));
    console.log(pad(`HTTP (MCP):  ${NGROK_URL}/mcp`));
    console.log(`╠${line}╣`);
    console.log(pad('CONNECT ChatGPT:'));
    console.log(pad('Settings → Connected Apps → Add MCP Server'));
    console.log(pad(`URL: ${NGROK_URL}/mcp`));
    console.log(`╚${line}╝`);
    console.log('');
});
