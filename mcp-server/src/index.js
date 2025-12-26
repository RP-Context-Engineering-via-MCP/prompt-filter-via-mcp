import express from 'express';
import cors from 'cors';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { z } from 'zod';

const app = express();
app.use(cors());
// app.use(express.json()); // Removed to avoid consuming stream for MCP


const mcpServer = new McpServer({
    name: "chat-app-backend",
    version: "1.0.0"
});

// Define the tool to process prompts
mcpServer.tool(
    "process_prompt",
    { prompt: z.string() },
    async ({ prompt }) => {
        // CRITICAL: Log the prompt as requested
        console.log(`[MCP Server] Received prompt: ${prompt}`);

        try {
            const response = await fetch('http://localhost:3003/filter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Filter engine returned error: ${response.status} - ${errorText}`);
                throw new Error(`Filter engine failed: ${response.status}`);
            }

            const data = await response.json();

            const analysisSummary = data.enriched_analysis
                ? JSON.stringify(data.enriched_analysis, null, 2)
                : "No analysis available";

            return {
                content: [{
                    type: "text",
                    text: `Redacted Text: ${data.redacted}\n\nAnalysis:\n${analysisSummary}`
                }]
            };
        } catch (error) {
            console.error("Error calling filter engine:", error);
            return {
                content: [{
                    type: "text",
                    text: `Error processing prompt: ${error.message}\n\n(Original: ${prompt})`
                }]
            };
        }
    }
);

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
