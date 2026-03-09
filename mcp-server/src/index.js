import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { randomUUID } from 'crypto';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js';
import { createMcpServer } from './tools.js';
import { verifyAuthToken } from './core/auth.js';
import { getOrCreateMcpSession, saveMcpSession, setCurrentSession, closeRedis, isHealthy } from './services/sessionService.js';
import { isFilterEngineHealthy } from './clients/filterClient.js';
import { isEnrichmentServiceHealthy } from './clients/enrichmentClient.js';
import { isUserMgmtServiceHealthy } from './clients/userMgmtClient.js';

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

// Health check endpoint
app.get('/health', async (req, res) => {
    try {
        const [redisHealthy, filterHealthy, enrichHealthy, userMgmtHealthy] = await Promise.all([
            isHealthy(),
            isFilterEngineHealthy(),
            isEnrichmentServiceHealthy(),
            isUserMgmtServiceHealthy()
        ]);

        res.json({
            status: 'ok',
            service: 'mcp-server',
            timestamp: new Date().toISOString(),
            dependencies: {
                redis: redisHealthy ? 'connected' : 'disconnected',
                filter_engine: filterHealthy ? 'healthy' : 'unhealthy',
                enrichment_service: enrichHealthy ? 'healthy' : 'unhealthy',
                user_management: userMgmtHealthy ? 'healthy' : 'unhealthy'
            }
        });
    } catch (error) {
        res.status(503).json({
            status: 'error',
            service: 'mcp-server',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// ─────────────────────────────────────────────
// Legacy SSE transport (Claude Desktop / web-client)
// ─────────────────────────────────────────────
app.get('/sse', verifyAuthToken, async (req, res) => {
    const userId = req.user_id;
    const jwtToken = req.headers.authorization?.slice(7) || null;  // Extract token from "Bearer <token>"
    console.log(`[SSE:connect] New SSE connection established for user: ${userId}`);
    res.setHeader('X-Accel-Buffering', 'no');
    const transport = new SSEServerTransport("/message", res);
    console.log(`[SSE:session] Assigned session ID: ${transport.sessionId}`);

    transports.set(transport.sessionId, transport);

    res.on('close', () => {
        console.log(`[SSE:close] Connection closed for session: ${transport.sessionId}`);
        transports.delete(transport.sessionId);
    });

    const mcpServer = createMcpServer(userId, jwtToken);
    await mcpServer.connect(transport);
});

app.post('/message', verifyAuthToken, async (req, res) => {
    const userId = req.user_id;
    const sessionId = req.query.sessionId;
    if (!sessionId) {
        console.error("[SSE:message] Missing sessionId in request");
        res.status(400).send("Missing sessionId");
        return;
    }

    const transport = transports.get(sessionId);
    if (!transport) {
        console.error(`[SSE:message] Session not found: ${sessionId}`);
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
app.post('/mcp', verifyAuthToken, async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];
    const userId = req.user_id;  // Extracted from JWT by verifyAuthToken middleware
    const jwtToken = req.headers.authorization?.slice(7) || null;  // Extract token from "Bearer <token>"

    console.log(`[MCP:POST] user=${userId} | attempting to get/create session | sessionId=${sessionId || 'new'}`);

    try {
        // Get or create user-scoped session
        const session = await getOrCreateMcpSession(userId, sessionId);
        
        // Set as user's current session
        await setCurrentSession(userId, session.id);

        if (session.id && httpTransports.has(session.id)) {
            // Route to existing session transport
            const transport = httpTransports.get(session.id);
            req.user_id = userId;
            req.session = session;
            await transport.handleRequest(req, res, req.body);
            
            // Save session after handling request
            await saveMcpSession(userId, session);
            return;
        }

        if (!sessionId && isInitializeRequest(req.body)) {
            // New session — create transport + MCP server
            const transport = new StreamableHTTPServerTransport({
                sessionIdGenerator: () => session.id,  // Use session service's generated ID
                onsessioninitialized: (newSessionId) => {
                    console.log(`[ChatGPT:MCP] MCP session initialized: ${newSessionId} | user_id: ${userId}`);
                    httpTransports.set(newSessionId, transport);
                }
            });

            transport.onclose = () => {
                if (transport.sessionId) {
                    console.log(`[ChatGPT:MCP] Session closed: ${transport.sessionId} | user_id: ${userId}`);
                    httpTransports.delete(transport.sessionId);
                }
            };

            const mcpServer = createMcpServer(userId, jwtToken);
            req.user_id = userId;
            req.session = session;
            await mcpServer.connect(transport);
            await transport.handleRequest(req, res, req.body);

            // Save session after initialization
            await saveMcpSession(userId, session);
            return;
        }

        res.status(400).json({ error: 'Bad request: missing or invalid session' });
    } catch (error) {
        console.error('[MCP:POST:error]', error);
        res.status(500).json({ error: 'Internal server error', detail: error.message });
    }
});

app.get('/mcp', verifyAuthToken, async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];
    const userId = req.user_id;
    const jwtToken = req.headers.authorization?.slice(7) || null;
    if (!sessionId || !httpTransports.has(sessionId)) {
        res.status(400).json({ error: 'Invalid or missing session ID' });
        return;
    }
    res.setHeader('X-Accel-Buffering', 'no');
    const transport = httpTransports.get(sessionId);
    req.user_id = userId;
    await transport.handleRequest(req, res);
});

app.delete('/mcp', verifyAuthToken, async (req, res) => {
    const sessionId = req.headers['mcp-session-id'];
    const userId = req.user_id;
    const jwtToken = req.headers.authorization?.slice(7) || null;
    if (!sessionId || !httpTransports.has(sessionId)) {
        res.status(400).json({ error: 'Invalid or missing session ID' });
        return;
    }
    const transport = httpTransports.get(sessionId);
    req.user_id = userId;
    await transport.handleRequest(req, res);
    httpTransports.delete(sessionId);
    console.log(`[ChatGPT:MCP] Session deleted: ${sessionId} | user_id: ${userId}`);
});

const PORT = process.env.PORT || 3001;
const server = app.listen(PORT, () => {
    console.log(`MCP Server running on port ${PORT}`);
    console.log(`  SSE transport:              http://localhost:${PORT}/sse`);
    console.log(`  Streamable HTTP transport:  http://localhost:${PORT}/mcp`);
    console.log(`  Health check:               http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('[SigTerm] shutting down gracefully...');
    server.close(async () => {
        console.log('[SigTerm] HTTP server closed');
        await closeRedis();
        process.exit(0);
    });
});

process.on('SIGINT', async () => {
    console.log('[SigInt] shutting down gracefully...');
    server.close(async () => {
        console.log('[SigInt] HTTP server closed');
        await closeRedis();
        process.exit(0);
    });
});
