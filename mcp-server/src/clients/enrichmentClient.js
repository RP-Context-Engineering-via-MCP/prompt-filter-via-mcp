/**
 * Enrichment Service Client
 * 
 * Calls the Enrichment Service API with internal service token authentication.
 * Only MCP Server (or other internal services) should call this — users never see the token.
 */

const ENRICHMENT_SERVICE_URL = process.env.ENRICHMENT_SERVICE_URL || 'http://127.0.0.1:3004';
const INTERNAL_SERVICE_TOKEN = process.env.INTERNAL_SERVICE_TOKEN || '';

/**
 * Call Enrichment Service to enrich a prompt with context
 * 
 * @param {Object} data - Enrichment request data
 * @param {string} data.prompt - User prompt
 * @param {string} data.user_id - User UUID
 * @param {string} data.source - Source mode ('mcp' or 'web_client')
 * @param {string} [data.mcp_client] - MCP client name (for source='mcp')
 * @param {string} [data.session_id] - Session ID
 * @returns {Promise<Object>} Enrichment response
 * @throws {Error} If enrichment service call fails
 */
export async function callEnrichmentService(data) {
    const url = `${ENRICHMENT_SERVICE_URL}/enrich`;

    const headers = {
        'Content-Type': 'application/json',
        'X-Service-Token': INTERNAL_SERVICE_TOKEN
    };

    try {
        console.log(`[EnrichClient] Calling Enrichment Service | user_id=${data.user_id} | source=${data.source} | prompt_len=${data.prompt.length}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(data),
            timeout: 15000
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[EnrichClient:error] Enrichment Service returned ${response.status} | ${errorText}`);
            throw new Error(`Enrichment Service error: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        console.log(`[EnrichClient:success] Enriched | turn=${result.turn_index} | session=${result.session_id} | latency=${result.latency_ms}ms`);
        
        return result;

    } catch (error) {
        console.error('[EnrichClient:exception]', error.message);
        throw error;
    }
}

/**
 * Check Enrichment Service health
 * 
 * @returns {Promise<boolean>} True if healthy
 */
export async function isEnrichmentServiceHealthy() {
    try {
        const response = await fetch(`${ENRICHMENT_SERVICE_URL}/health`, {
            timeout: 5000
        });
        return response.ok;
    } catch (error) {
        console.error('[EnrichClient:health_error]', error.message);
        return false;
    }
}
