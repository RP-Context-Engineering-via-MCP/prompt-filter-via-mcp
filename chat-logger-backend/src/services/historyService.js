import mongoose from 'mongoose';

const historySchema = new mongoose.Schema({
    id: { type: String, required: true },
    userId: { type: String, required: true },
    selected_session_id: { type: String, required: false },
    title: { type: String, required: true },
    date: { type: Date, default: Date.now },
    model: { type: String, required: true },
    messages: { type: Array, required: true },
    updatedAt: { type: Date, default: Date.now }
});

export const WebAppHistory = mongoose.model('WebAppHistory', historySchema, 'webAppHistory');

export const historyService = {
    /**
     * Retrieve all chat histories for a given user.
     * @param {string} userId - The ID of the user.
     * @returns {Promise<Array>} List of chat objects, sorted by date descending.
     */
    async getHistoryByUserId(userId) {
        // Fetch all documents for this userId, sorted newest first
        const history = await WebAppHistory.find({ userId }).sort({ date: -1 }).lean();
        return history;
    },

    /**
     * Save a new chat or update an existing one.
     * @param {string} userId - The user ID.
     * @param {object} chatData - The chat object (id, title, date, model, messages).
     * @returns {Promise<object>} The result of the operation.
     */
    async saveOrUpdateChat(userId, chatData) {
        const { id, title, date, model, messages } = chatData;

        // Fetch the user's current selected session from the user management service
        let selected_session_id = null;
        try {
            const effectiveUserId = userId || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2';
            const sessionRes = await fetch(`http://localhost:8080/api/users/${effectiveUserId}/current-session`);
            if (sessionRes.ok) {
                const sessionData = await sessionRes.json();
                if (sessionData.current_session_id) {
                    selected_session_id = sessionData.current_session_id;
                }
            }
        } catch (error) {
            console.error(`[historyService] Failed to fetch current session for user ${userId}:`, error.message);
        }

        // Upsert based on chatId (provided as id in the chatData object)
        const filter = { id, userId };
        const update = {
            id,
            userId,
            selected_session_id,
            title,
            date: date ? new Date(date) : new Date(),
            model: model || 'unknown',
            messages,
            updatedAt: new Date()
        };

        const result = await WebAppHistory.findOneAndUpdate(filter, update, {
            upsert: true,
            returnDocument: 'after'
        });

        return { success: true, result };
    }
};
