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
            console.info(`[INFO] MCP Server received 'process_prompt'. Prompt: "${prompt}". Calling Prompt Enrichment Service at http://127.0.0.1:3004/enrich...`);
            console.log(`[MCP Server] Received prompt: ${prompt} | Filter Enabled: ${enable_filter}`);

            try {
                // 1. Process through Prompt Enrichment Service using the received prompt (which is already secured if filter was enabled)
                const enrichResponse = await fetch('http://127.0.0.1:3004/enrich', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt, user_id: "5ca4d3ee-a139-44f9-9f9a-84655025a8f2" })
                });

                if (!enrichResponse.ok) {
                    const errorText = await enrichResponse.text();
                    console.error(`Enrichment service returned error: ${enrichResponse.status} - ${errorText}`);
                    return {
                        content: [{
                            type: "text",
                            text: JSON.stringify({ error: `Context Engine functionality unavailable (Error ${enrichResponse.status}). Ensure API Keys are valid and the Service is running.` })
                        }]
                    };
                }

                const enrichData = await enrichResponse.json();

                // 2. Format final response logic as JSON
                const responsePayload = {
                    llm_response: enrichData.llm_response,
                    turn_index: enrichData.turn_index,
                    enriched_prompt: enrichData.enriched_prompt
                };

                return {
                    content: [{
                        type: "text",
                        text: JSON.stringify(responsePayload)
                    }]
                };

            } catch (error) {
                console.error("Error processing prompt:", error);
                return {
                    content: [{
                        type: "text",
                        text: JSON.stringify({ error: `Error processing prompt: ${error.message}. Please check if the services are running.` })
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
            console.info(`[INFO] MCP Server received 'capture_chat'. Calling Chat Logger Backend to log chat for session: ${session_id || 'none'}`);
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
