/**
 * API Service — POSTs chat log data to the Chat Logger Backend
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:3005';

/**
 * Log a chat interaction to the backend
 * @param {Object} data - Chat log data
 * @param {string} data.user_prompt - The user's message
 * @param {string} data.llm_response - The LLM's response
 * @param {string} [data.session_id] - Session identifier
 * @param {string} [data.source] - Source client (e.g. "claude_desktop")
 * @param {Object} [data.metadata] - Additional metadata
 */
export async function logChat(data) {
    try {
        const response = await fetch(`${BACKEND_URL}/api/chats`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[apiService] Backend returned ${response.status}: ${errorText}`);
            return { success: false, error: errorText };
        }

        const result = await response.json();
        console.log(`[apiService] Chat logged successfully, id: ${result._id}`);
        return { success: true, id: result._id };
    } catch (error) {
        console.error(`[apiService] Failed to log chat:`, error.message);
        return { success: false, error: error.message };
    }
}
