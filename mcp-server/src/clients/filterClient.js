/**
 * Filter Engine Client
 * 
 * Calls the Filter Engine API with internal service token authentication.
 * Only MCP Server (or other internal services) should call this — users never see the token.
 */

const FILTER_ENGINE_URL = process.env.FILTER_ENGINE_URL || 'http://127.0.0.1:3003';
const INTERNAL_SERVICE_TOKEN = process.env.INTERNAL_SERVICE_TOKEN || '';

/**
 * Call Filter Engine to redact/filter a prompt
 * 
 * @param {string} prompt - User prompt to filter
 * @returns {Promise<Object>} Filter response with original, redacted, labeled, enriched_analysis
 * @throws {Error} If filter engine call fails
 */
export async function callFilterEngine(prompt) {
    const url = `${FILTER_ENGINE_URL}/filter`;
    
    const headers = {
        'Content-Type': 'application/json',
        'X-Service-Token': INTERNAL_SERVICE_TOKEN
    };

    try {
        console.log(`[FilterClient] Calling Filter Engine | prompt_len=${prompt.length} | url=${url}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ prompt: prompt }),
            timeout: 10000
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[FilterClient:error] Filter Engine returned ${response.status} | ${errorText}`);
            throw new Error(`Filter Engine error: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log(`[FilterClient:success] Filter engine processed | redacted_len=${data.redacted.length} | entities=${data.enriched_analysis.length}`);
        
        return data;

    } catch (error) {
        console.error('[FilterClient:exception]', error.message);
        throw error;
    }
}

/**
 * Check Filter Engine health
 * 
 * @returns {Promise<boolean>} True if healthy
 */
export async function isFilterEngineHealthy() {
    try {
        const response = await fetch(`${FILTER_ENGINE_URL}/health`, {
            timeout: 5000
        });
        return response.ok;
    } catch (error) {
        console.error('[FilterClient:health_error]', error.message);
        return false;
    }
}
