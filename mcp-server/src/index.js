import express from 'express';
import cors from 'cors';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { createMcpServer } from './tools.js';

const app = express();
app.use(cors());
// app.use(express.json()); // Removed to avoid consuming stream for MCP

let transports = new Map();

// Add a root route for browser verification
app.get('/', (req, res) => {
    res.send('MCP Server is running. Use the Web Client to chat.');
});

app.get('/sse', async (req, res) => {
    console.log("New SSE connection established");
    const transport = new SSEServerTransport("/message", res);
    console.log(`Assigned session ID: ${transport.sessionId}`);

    // Store transport by sessionId
    transports.set(transport.sessionId, transport);

    // Clean up on close
    res.on('close', () => {
        console.log(`Connection closed for session: ${transport.sessionId}`);
        transports.delete(transport.sessionId);
    });

    // Each connection gets its own McpServer instance to avoid transport conflicts
    const mcpServer = createMcpServer();
    await mcpServer.connect(transport);
});

app.post('/message', async (req, res) => {
    // console.log("Received POST /message request");

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

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`MCP Server running on port ${PORT}`);
});
