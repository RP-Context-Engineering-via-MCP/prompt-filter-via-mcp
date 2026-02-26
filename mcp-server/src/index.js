import express from 'express';
import cors from 'cors';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { z } from 'zod';
import { spawn } from 'child_process';
import path from 'path';

const app = express();
app.use(cors());
// app.use(express.json()); // Removed to avoid consuming stream for MCP

// Factory function: creates a new McpServer with tools registered per connection
function createMcpServer() {
    const server = new McpServer({
        name: "chat-app-backend",
        version: "1.0.0"
    });

    // Define the tool to process prompts
    server.tool(
        "process_prompt",
        {
            prompt: z.string(),
            enable_filter: z.boolean().optional().default(true)
        },
        async ({ prompt, enable_filter }) => {
            console.log(`[MCP Server] Received prompt: ${prompt} | Filter Enabled: ${enable_filter}`);

            try {
                let securedPrompt = prompt;
                let pfeData = null;

                // 1. Process through Prompt Filter Engine if ON
                if (enable_filter) {
                    const filterResponse = await fetch('http://localhost:3003/filter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt })
                    });

                    if (!filterResponse.ok) {
                        const errorText = await filterResponse.text();
                        console.error(`Filter engine returned error: ${filterResponse.status} - ${errorText}`);
                        return {
                            content: [{
                                type: "text",
                                text: `Filter engine functionality unavailable (Error ${filterResponse.status}). Please ensure the PFE service is running on Port 3003.`
                            }]
                        };
                    }

                    pfeData = await filterResponse.json();
                    securedPrompt = pfeData.redacted;
                }

                // 2. Process through Prompt Enrichment Service
                const enrichResponse = await fetch('http://localhost:3004/enrich', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: securedPrompt })
                });

                if (!enrichResponse.ok) {
                    const errorText = await enrichResponse.text();
                    console.error(`Enrichment service returned error: ${enrichResponse.status} - ${errorText}`);
                    return {
                        content: [{
                            type: "text",
                            text: `Context Engine functionality unavailable (Error ${enrichResponse.status}). Please ensure the Prompt Enrichment Service is running on Port 3004.`
                        }]
                    };
                }

                const enrichData = await enrichResponse.json();
                const llmAnswer = enrichData.llm_response;

                // 3. Format final response logic
                let formattedResponse = "";

                if (enable_filter && pfeData) {
                    const analysisSummary = pfeData.enriched_analysis
                        ? JSON.stringify(pfeData.enriched_analysis, null, 2)
                        : "No analysis available";

                    formattedResponse = `User Prompt:
${prompt}

PII Detection Prompt:
${pfeData.labeled}

Secured Prompt:
${pfeData.redacted}

Analysis:
${analysisSummary}

---
AI Response:
${llmAnswer}`;
                } else {
                    formattedResponse = `${llmAnswer}`;
                }

                return {
                    content: [{
                        type: "text",
                        text: formattedResponse
                    }]
                };

            } catch (error) {
                console.error("Error processing prompt:", error);
                return {
                    content: [{
                        type: "text",
                        text: `Error processing prompt: ${error.message}. Please check if the services are running.`
                    }]
                };
            }
        }
    );

    return server;
}

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
