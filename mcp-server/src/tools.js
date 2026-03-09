import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { logChat } from './services/apiService.js';
import { callEnrichmentService } from './clients/enrichmentClient.js';
import { getUserProfile, extractJwtFromHeader } from './clients/userMgmtClient.js';
import { assembleSystemMessage, buildEnrichedUserMessage, extractProfileFields } from './services/atceService.js';

// Factory function: creates a new McpServer with tools registered per connection
// Now accepts authenticated user_id and optional jwtToken for profile fetching
export function createMcpServer(userId = null, jwtToken = null) {
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
            // Use authenticated user_id from JWT, fallback to environment default if needed
            const user_id = userId || process.env.DEFAULT_USER_ID || "5ca4d3ee-a139-44f9-9f9a-84655025a8f2";

            console.info(`[INFO] MCP Server received 'process_prompt'. source=${source} | client_name=${client_name} | user_id=${user_id} | prompt="${prompt}". Calling Prompt Enrichment Service...`);
            console.log(`[MCP Server] process_prompt | source=${source} | client_name=${client_name} | Filter Enabled: ${enable_filter}`);

            try {
                // 0. Fetch user profile if JWT available (for personalized context)
                let userProfile = null;
                if (jwtToken) {
                    userProfile = await getUserProfile(user_id, jwtToken);
                    if (userProfile) {
                        console.info(`[INFO] User profile loaded | profile_mode=${userProfile.profile_mode || 'default'}`);
                    }
                }

                // 1. Process through Prompt Enrichment Service with source mode
                // Uses internal service token for secure service-to-service communication
                const enrichmentRequest = {
                    prompt: prompt,
                    user_id: user_id,
                    source: source,
                    mcp_client: client_name
                };

                // Include user profile info if available
                if (userProfile) {
                    enrichmentRequest.user_profile = extractProfileFields(userProfile);
                }

                const enrichData = await callEnrichmentService(enrichmentRequest);

                console.info(`[INFO] Enrichment response received | source=${source} | session=${enrichData.session_id} | turn=${enrichData.turn_index} | has_llm_response=${!!enrichData.llm_response}`);

                // 2. Format response based on source mode
                if (source === "mcp") {
                    // MCP mode: return enriched prompt (behaviors) — LLM app uses this as context
                    // Include user profile context in the enriched prompt
                    let enhancedPrompt = enrichData.enriched_prompt;
                    
                    if (userProfile) {
                        enhancedPrompt = assembleSystemMessage(userProfile, null, enrichData.enriched_prompt);
                    }

                    return {
                        content: [{
                            type: "text",
                            text: enhancedPrompt
                        }]
                    };
                }

                // web_client mode: return LLM response as JSON
                const responsePayload = {
                    llm_response: enrichData.llm_response,
                    turn_index: enrichData.turn_index,
                    enriched_prompt: enrichData.enriched_prompt,
                    has_user_profile: !!userProfile
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
            user_id: z.string().optional().describe("User ID for associating chat logs")
        },
        async ({ user_prompt, llm_response, session_id, source, model, user_id: paramUserId }) => {
            // Use authenticated user_id from JWT, fallback to parameter, then to environment default
            const resolvedUserId = userId || paramUserId || process.env.DEFAULT_USER_ID || "5ca4d3ee-a139-44f9-9f9a-84655025a8f2";
            
            console.info(`[INFO] MCP Server received 'capture_chat'. user_id=${resolvedUserId} | session=${session_id || 'none'} | source=${source}`);
            console.log(`[MCP Server] capture_chat called | user_id: ${resolvedUserId} | session: ${session_id || 'none'} | source: ${source} | prompt_len: ${user_prompt.length} | response_len: ${llm_response.length}`);

            try {
                const result = await logChat({
                    user_prompt,
                    llm_response,
                    session_id,
                    source,
                    user_id: resolvedUserId,
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
