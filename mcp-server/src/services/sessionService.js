/**
 * MCP Server Session Service
 * 
 * Manages user-scoped session storage using Redis.
 * Provides functions to create, retrieve, and persist session data per user.
 * 
 * Session Key Structure:
 *   - Session data: `mcp:session:{user_id}:{session_id}`
 *   - Current session: `mcp:user:{user_id}:current_session`
 * 
 * Session TTL: 1 hour (configurable via MCP_SESSION_TTL env var)
 */

import { createClient } from 'redis';
import { randomUUID } from 'crypto';

const SESSION_TTL_SECONDS = parseInt(process.env.MCP_SESSION_TTL || '3600', 10);
const MCP_SESSION_PREFIX = 'mcp:session:';
const MCP_USER_CURRENT_PREFIX = 'mcp:user:';
const MCP_CURRENT_SUFFIX = ':current_session';

let redisClient = null;
let isConnecting = false;
let connectionError = null;

/**
 * Initialize Redis client (lazy connection)
 */
async function getRedisClient() {
    if (redisClient && redisClient.isOpen) {
        return redisClient;
    }

    if (isConnecting) {
        // Wait for connection to complete
        return new Promise((resolve, reject) => {
            const checkInterval = setInterval(() => {
                if (redisClient && redisClient.isOpen) {
                    clearInterval(checkInterval);
                    resolve(redisClient);
                } else if (connectionError) {
                    clearInterval(checkInterval);
                    reject(connectionError);
                }
            }, 50);
        });
    }

    isConnecting = true;
    try {
        const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
        redisClient = createClient({ url: redisUrl });

        redisClient.on('error', (err) => {
            console.error('[SessionService:redis_error]', err);
            connectionError = err;
        });

        redisClient.on('connect', () => {
            console.log('[SessionService:redis_connected]');
            connectionError = null;
        });

        await redisClient.connect();
        console.log('[SessionService:redis] Connected to Redis');
        return redisClient;
    } catch (error) {
        connectionError = error;
        console.error('[SessionService:connection_error]', error);
        throw error;
    } finally {
        isConnecting = false;
    }
}

/**
 * Generate session key for Redis storage
 */
function getSessionKey(userId, sessionId) {
    return `${MCP_SESSION_PREFIX}${userId}:${sessionId}`;
}

/**
 * Generate key for tracking user's current active session
 */
function getCurrentSessionKey(userId) {
    return `${MCP_USER_CURRENT_PREFIX}${userId}${MCP_CURRENT_SUFFIX}`;
}

/**
 * Get or create a session for this user
 * 
 * @param {string} userId - Authenticated user ID from JWT
 * @param {string|null} sessionId - Optional existing session ID to resume
 * @returns {Promise<Object>} Session object with id, user_id, tier1_messages, etc.
 */
export async function getOrCreateMcpSession(userId, sessionId = null) {
    try {
        // If client provides a session_id, try to load it
        if (sessionId) {
            const client = await getRedisClient();
            const key = getSessionKey(userId, sessionId);
            const data = await client.get(key);

            if (data) {
                const session = JSON.parse(data);
                console.log(`[SessionService:load] user=${userId} session=${sessionId} loaded from Redis`);
                return session;
            }
            // Session not found or belongs to different user — fall through and create new
        }

        // Create a fresh session scoped to this user
        const newSessionId = randomUUID();
        const session = {
            id: newSessionId,
            user_id: userId,
            tier1_messages: [],
            tier2_summaries: [],
            tier3_core_memory: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        // Save to Redis
        const client = await getRedisClient();
        const key = getSessionKey(userId, newSessionId);
        await client.setEx(
            key,
            SESSION_TTL_SECONDS,
            JSON.stringify(session)
        );

        // Track as user's current session
        const currentKey = getCurrentSessionKey(userId);
        await client.setEx(
            currentKey,
            SESSION_TTL_SECONDS,
            newSessionId
        );

        console.log(`[SessionService:create] user=${userId} session=${newSessionId} created`);
        return session;

    } catch (error) {
        console.error('[SessionService:get_or_create_error]', error);
        // Fallback: return in-memory session if Redis fails
        const newSessionId = randomUUID();
        return {
            id: newSessionId,
            user_id: userId,
            tier1_messages: [],
            tier2_summaries: [],
            tier3_core_memory: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };
    }
}

/**
 * Save/update an existing session in Redis
 * 
 * @param {string} userId - User ID
 * @param {Object} session - Session object to persist
 * @returns {Promise<void>}
 */
export async function saveMcpSession(userId, session) {
    try {
        if (!session.id) {
            console.error('[SessionService:save_error] Session missing id field');
            return;
        }

        // Update timestamp
        session.updated_at = new Date().toISOString();

        const client = await getRedisClient();
        const key = getSessionKey(userId, session.id);

        await client.setEx(
            key,
            SESSION_TTL_SECONDS,
            JSON.stringify(session)
        );

        console.log(`[SessionService:save] user=${userId} session=${session.id} persisted | messages=${session.tier1_messages.length}`);

    } catch (error) {
        console.error('[SessionService:save_error]', error);
        // Non-fatal: log but don't throw
    }
}

/**
 * Set (or update) the user's current active session
 * 
 * @param {string} userId - User ID
 * @param {string} sessionId - Session ID to mark as current
 * @returns {Promise<void>}
 */
export async function setCurrentSession(userId, sessionId) {
    try {
        const client = await getRedisClient();
        const key = getCurrentSessionKey(userId);

        await client.setEx(
            key,
            SESSION_TTL_SECONDS,
            sessionId
        );

        console.log(`[SessionService:set_current] user=${userId} current_session=${sessionId}`);

    } catch (error) {
        console.error('[SessionService:set_current_error]', error);
        // Non-fatal
    }
}

/**
 * Get the user's current active session ID (if tracking it)
 * 
 * @param {string} userId - User ID
 * @returns {Promise<string|null>} Session ID or null if not found
 */
export async function getCurrentSession(userId) {
    try {
        const client = await getRedisClient();
        const key = getCurrentSessionKey(userId);
        const sessionId = await client.get(key);

        if (sessionId) {
            console.log(`[SessionService:get_current] user=${userId} current_session=${sessionId}`);
        }

        return sessionId;

    } catch (error) {
        console.error('[SessionService:get_current_error]', error);
        return null;
    }
}

/**
 * Delete a session (from both cache and Redis)
 * 
 * @param {string} userId - User ID
 * @param {string} sessionId - Session ID to delete
 * @returns {Promise<void>}
 */
export async function deleteMcpSession(userId, sessionId) {
    try {
        const client = await getRedisClient();
        const key = getSessionKey(userId, sessionId);

        await client.del(key);
        console.log(`[SessionService:delete] user=${userId} session=${sessionId} deleted from Redis`);

    } catch (error) {
        console.error('[SessionService:delete_error]', error);
        // Non-fatal
    }
}

/**
 * Health check: verify Redis connectivity
 * 
 * @returns {Promise<boolean>} True if Redis is reachable
 */
export async function isHealthy() {
    try {
        const client = await getRedisClient();
        const pong = await client.ping();
        return pong === 'PONG';
    } catch (error) {
        console.error('[SessionService:health_check_error]', error);
        return false;
    }
}

/**
 * Close Redis connection (on server shutdown)
 */
export async function closeRedis() {
    if (redisClient && redisClient.isOpen) {
        await redisClient.quit();
        console.log('[SessionService:redis_closed]');
    }
}
