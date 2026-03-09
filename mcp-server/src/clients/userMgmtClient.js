/**
 * User Management Service Client
 * 
 * Fetches user profile from User Management Service for personalization.
 * Uses the user's own JWT token for authentication.
 * 
 * Fails gracefully — if User Mgmt Service is unavailable, continues without profile.
 */

const USER_MGMT_SERVICE_URL = process.env.USER_MGMT_SERVICE_URL || 'http://localhost:8000';

/**
 * Fetch user profile from User Management Service
 * 
 * @param {string} userId - User UUID
 * @param {string} jwtToken - User's JWT token (from Authorization header)
 * @returns {Promise<Object|null>} User profile or null if fetch fails
 */
export async function getUserProfile(userId, jwtToken) {
    if (!userId || !jwtToken) {
        console.warn('[UserMgmtClient:get_profile] Missing userId or jwtToken');
        return null;
    }

    try {
        const url = `${USER_MGMT_SERVICE_URL}/api/users/${userId}`;
        
        console.log(`[UserMgmtClient:get_profile] Fetching profile for user=${userId}`);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${jwtToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 5000
        });

        if (response.status === 200) {
            const profile = await response.json();
            console.log(`[UserMgmtClient:success] Profile fetched | profile_mode=${profile.profile_mode || 'default'} | profile_id=${profile.predefined_profile_id || 'none'}`);
            return profile;
        }

        if (response.status === 404) {
            console.warn(`[UserMgmtClient:not_found] User not found: ${userId}`);
            return null;
        }

        console.warn(`[UserMgmtClient:http_error] User Mgmt Service returned ${response.status}`);
        return null;

    } catch (error) {
        // Fail gracefully — don't block chat if User Mgmt Service is down
        console.warn('[UserMgmtClient:error]', error.message, '— continuing without profile');
        return null;
    }
}

/**
 * Extract JWT token from Authorization header
 * 
 * @param {string} authHeader - Authorization header value (e.g., "Bearer <token>")
 * @returns {string|null} JWT token or null
 */
export function extractJwtFromHeader(authHeader) {
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return null;
    }
    return authHeader.slice(7); // Remove "Bearer " prefix
}

/**
 * Check User Management Service health
 * 
 * @returns {Promise<boolean>} True if healthy
 */
export async function isUserMgmtServiceHealthy() {
    try {
        const response = await fetch(`${USER_MGMT_SERVICE_URL}/health`, {
            timeout: 5000
        });
        return response.ok;
    } catch (error) {
        console.warn('[UserMgmtClient:health_error]', error.message);
        return false;
    }
}
