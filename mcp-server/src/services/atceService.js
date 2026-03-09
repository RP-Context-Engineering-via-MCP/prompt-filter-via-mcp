/**
 * ATCE Service — Assembles tiered conversation context for LLM system prompts
 * 
 * Integrates user profile, behavior context, and conversation history
 * into a cohesive system message that guides LLM behavior.
 */

/**
 * Build a system message enriched with user profile
 * 
 * @param {Object} userProfile - User profile from User Management Service
 * @param {Object} session - Session object with conversation history
 * @param {string} baseSystemPrompt - Optional base system instructions
 * @returns {string} Assembled system message
 */
export function assembleSystemMessage(userProfile, session, baseSystemPrompt = null) {
    const systemParts = [];

    // 1. Base system instructions
    if (baseSystemPrompt) {
        systemParts.push(baseSystemPrompt);
    } else {
        systemParts.push(getDefaultSystemInstructions());
    }

    // 2. User profile context
    if (userProfile) {
        systemParts.push(buildProfileContext(userProfile));
    }

    // 3. Session/conversation memory context
    if (session && session.tier3_core_memory) {
        systemParts.push(buildMemoryContext(session));
    }

    return systemParts.join('\n\n');
}

/**
 * Default system instructions if none provided
 */
function getDefaultSystemInstructions() {
    return `You are a helpful AI assistant. Respond to user queries accurately and concisely.
Follow any user preferences and behavior patterns indicated in the profile and conversation context below.`;
}

/**
 * Build user profile context section
 */
function buildProfileContext(profile) {
    const parts = ['## User Profile'];

    if (profile.profile_mode) {
        parts.push(`- Mode: ${profile.profile_mode}`);
    }

    if (profile.predefined_profile_id) {
        parts.push(`- Profile ID: ${profile.predefined_profile_id}`);
    }

    if (profile.account_status) {
        parts.push(`- Account Status: ${profile.account_status}`);
    }

    if (profile.user_preferences) {
        parts.push(`- Preferences: ${JSON.stringify(profile.user_preferences)}`);
    }

    if (profile.role) {
        parts.push(`- Role: ${profile.role}`);
    }

    if (profile.organization) {
        parts.push(`- Organization: ${profile.organization}`);
    }

    return parts.join('\n');
}

/**
 * Build conversation memory context section
 */
function buildMemoryContext(session) {
    const parts = ['## Established Context'];

    if (session.tier3_core_memory) {
        parts.push(`Core Memory: ${session.tier3_core_memory}`);
    }

    const recentMessages = session.tier1_messages?.slice(-5) || [];
    if (recentMessages.length > 0) {
        parts.push('Recent Conversation:');
        recentMessages.forEach((msg) => {
            const role = msg.role === 'user' ? 'User' : 'Assistant';
            parts.push(`- ${role}: ${msg.content.substring(0, 100)}${msg.content.length > 100 ? '...' : ''}`);
        });
    }

    return parts.join('\n');
}

/**
 * Build enriched behavior context from enrichment service response
 * 
 * @param {Object} enrichResponse - Response from Enrichment Service
 * @returns {string} Behavior context section
 */
export function buildBehaviorContext(enrichResponse) {
    const parts = ['## Behavioral Context'];

    if (enrichResponse.behavior) {
        parts.push(`Behavior Profile: ${enrichResponse.behavior}`);
    }

    if (enrichResponse.core_behavior) {
        parts.push(`Core Behavior: ${enrichResponse.core_behavior}`);
    }

    if (enrichResponse.profile_context) {
        parts.push(`Profile Context: ${enrichResponse.profile_context}`);
    }

    return parts.join('\n');
}

/**
 * Format user messages with context for LLM input
 * 
 * @param {string} userPrompt - Original user prompt
 * @param {Object} enrichResponse - Optional enriched context from Enrichment Service
 * @param {Object} userProfile - Optional user profile
 * @returns {string} Formatted user message with context
 */
export function buildEnrichedUserMessage(userPrompt, enrichResponse = null, userProfile = null) {
    const parts = [userPrompt];

    if (enrichResponse && enrichResponse.enriched_prompt) {
        parts.push(`\n[System Context]: ${enrichResponse.enriched_prompt}`);
    }

    if (userProfile && userProfile.instructions) {
        parts.push(`\n[User Instructions]: ${userProfile.instructions}`);
    }

    return parts.join('\n');
}

/**
 * Extract relevant profile fields for inline use
 * 
 * @param {Object} profile - User profile
 * @returns {Object} Extracted fields
 */
export function extractProfileFields(profile) {
    if (!profile) return {};

    return {
        userId: profile.id || profile.user_id,
        profileMode: profile.profile_mode,
        profileId: profile.predefined_profile_id,
        organization: profile.organization,
        role: profile.role,
        tier: profile.tier || 'free',
        preferences: profile.user_preferences || {},
        isAdmin: profile.is_admin || false,
        isVerified: profile.is_verified || false
    };
}
