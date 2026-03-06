import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { logChat } from './services/apiService.js';

// Factory function: creates a new McpServer with tools registered per connection
export function createMcpServer() {
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

    // Tool to capture and log chat interactions to the backend
    server.tool(
        "capture_chat",
        {
            user_prompt: z.string().describe("The user's original message"),
            llm_response: z.string().describe("The LLM's generated response"),
            session_id: z.string().optional().describe("Session identifier to group conversations"),
            source: z.string().optional().default("claude_desktop").describe("Source client name"),
            model: z.string().optional().describe("AI model name if detectable")
        },
        async ({ user_prompt, llm_response, session_id, source, model }) => {
            console.log(`[MCP Server] capture_chat called | session: ${session_id || 'none'} | source: ${source}`);

            try {
                const result = await logChat({
                    user_prompt,
                    llm_response,
                    session_id,
                    source,
                    metadata: { model }
                });

                if (result.success) {
                    return {
                        content: [{
                            type: "text",
                            text: `Chat logged successfully (id: ${result.id})`
                        }]
                    };
                } else {
                    return {
                        content: [{
                            type: "text",
                            text: `Failed to log chat: ${result.error}`
                        }]
                    };
                }
            } catch (error) {
                console.error("Error in capture_chat:", error);
                return {
                    content: [{
                        type: "text",
                        text: `Error logging chat: ${error.message}`
                    }]
                };
            }
        }
    );

    return server;
}
