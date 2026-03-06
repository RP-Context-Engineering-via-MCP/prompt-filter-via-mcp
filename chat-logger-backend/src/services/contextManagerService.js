import { ChatLog } from '../models/db.js';

const CONTEXT_MANAGER_URL = process.env.CONTEXT_MANAGER_URL || 'http://localhost:8000';

// In-memory cache to store logs before condensation
const sessionCache = new Map();

/**
 * Caches logs and triggers condensation when 2 log pairs (4 messages) are collected.
 * If met, fires off the condensation API call asynchronously.
 */
export async function checkAndTriggerCondensation(session_id, user_prompt, llm_response) {
    if (!session_id || !user_prompt || !llm_response) return;

    try {
        if (!sessionCache.has(session_id)) {
            sessionCache.set(session_id, []);
        }

        const cache = sessionCache.get(session_id);
        cache.push({ role: 'user', content: user_prompt });
        cache.push({ role: 'assistant', content: llm_response });

        // If we have collected 2 full pairs (user + assistant * 2 = 4 messages)
        if (cache.length >= 4) {
            console.log(`[Condensation] Session ${session_id} reached 2 pairs in cache. Triggering condense...`);

            // Create a copy to send, and immediately clear the buffer
            const messagesToSend = [...cache];
            sessionCache.delete(session_id);

            // Fire and forget so we don't block
            triggerCondensation(session_id, messagesToSend);
        }
    } catch (error) {
        console.error(`[Condensation] Error in cache-based check for condensation:`, error.message);
    }
}

/**
 * Sends the provided messages to the Condensation API, or fetches from DB if manually triggered.
 */
export async function triggerCondensation(session_id, cachedMessages = null) {
    try {
        let messages = cachedMessages;

        // If no cached messages were provided (e.g., manual trigger testing endpoint)
        if (!messages) {
            // Fetch the latest 2 chat logs
            // sorted by descending order so [0] is latest, [1] is older
            const latestLogs = await ChatLog.find({ session_id })
                .sort({ timestamp: -1 })
                .limit(2);

            if (latestLogs.length < 2) {
                console.log(`[Condensation] Expected at least 2 logs but found ${latestLogs.length}`);
                return;
            }

            // The API expects messages in chronological order as a single batch,
            // so we reverse the logs to start from the oldest of the 2.
            latestLogs.reverse();

            messages = [];
            latestLogs.forEach(log => {
                messages.push({ role: 'user', content: log.user_prompt });
                messages.push({ role: 'assistant', content: log.llm_response });
            });
        }

        const payload = { messages };

        console.log(`[Condensation] Sending request to contextManager for session ${session_id}...`);

        const response = await fetch(`${CONTEXT_MANAGER_URL}/api/v1/session/${session_id}/condense`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API returned ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log(`[Condensation] Successfully condensed session ${session_id}. Decision appended: ${data.decision_appended}`);
    } catch (error) {
        console.error(`[Condensation] Failed to call condensation API for session ${session_id}:`, error.message);
    }
}
