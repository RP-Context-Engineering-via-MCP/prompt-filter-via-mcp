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
            enable_filter: z.boolean().optional().default(true),
            source: z.string().optional().default("mcp").describe("Source mode: 'mcp' for LLM web apps, 'web_client' for own platform"),
            client_name: z.string().optional().describe("Name of the LLM client (e.g., 'claude_web', 'claude_desktop', 'chatgpt', 'gemini')")
        },
        async ({ prompt, enable_filter, source, client_name }) => {
            // FIXME: user_id is hardcoded — replace with actual user authentication when JWT/auth is implemented
            const user_id = "5ca4d3ee-a139-44f9-9f9a-84655025a8f2";

            console.info(`[INFO] MCP Server received 'process_prompt'. source=${source} | client_name=${client_name} | user_id=${user_id} | prompt="${prompt}". Calling Prompt Enrichment Service...`);
            console.log(`[MCP Server] process_prompt | source=${source} | client_name=${client_name} | Filter Enabled: ${enable_filter}`);

            try {
                // Determine API URL (use env var or fallback to localhost)
                const apiUrl = process.env.PROMPT_ENRICHMENT_API_URL || 'http://localhost:3004';
                
                // 1. Process through Prompt Enrichment Service with source mode
                const enrichResponse = await fetch(`${apiUrl}/enrich`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt, user_id: user_id, source: source, mcp_client: client_name })
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

                console.info(`[INFO] Enrichment response received | source=${source} | session=${enrichData.session_id} | turn=${enrichData.turn_index} | has_llm_response=${!!enrichData.llm_response}`);

                // 2. Format response based on source mode
                if (source === "mcp") {
                    // MCP mode: return enriched prompt (behaviors) — LLM app uses this as context
                    return {
                        content: [{
                            type: "text",
                            text: enrichData.enriched_prompt
                        }]
                    };
                }

                // web_client mode: return LLM response as JSON
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
            model: z.string().optional().describe("AI model name if detectable"),
            // FIXME: user_id is hardcoded — replace with actual user authentication (JWT/session-based)
            // when auth is implemented. Currently uses a default user ID for development.
            user_id: z.string().optional().default("5ca4d3ee-a139-44f9-9f9a-84655025a8f2").describe("User ID for associating chat logs")
        },
        async ({ user_prompt, llm_response, session_id, source, model, user_id }) => {
            console.info(`[INFO] MCP Server received 'capture_chat'. user_id=${user_id} | session=${session_id || 'none'} | source=${source}`);
            console.log(`[MCP Server] capture_chat called | user_id: ${user_id} | session: ${session_id || 'none'} | source: ${source} | prompt_len: ${user_prompt.length} | response_len: ${llm_response.length}`);

            try {
                const result = await logChat({
                    user_prompt,
                    llm_response,
                    session_id,
                    source,
                    user_id,
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
