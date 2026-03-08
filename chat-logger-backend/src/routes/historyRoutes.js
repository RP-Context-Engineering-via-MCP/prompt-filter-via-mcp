import express from 'express';
import { historyService } from '../services/historyService.js';

const router = express.Router();

// GET /api/history/:userId
// Retrieve all chat histories for a specific user
router.get('/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        if (!userId) {
            return res.status(400).json({ success: false, error: 'userId parameter is required' });
        }

        const history = await historyService.getHistoryByUserId(userId);
        res.status(200).json({ success: true, count: history.length, data: history });
    } catch (error) {
        console.error('Error fetching chat history:', error);
        res.status(500).json({ success: false, error: 'Internal server error while fetching history' });
    }
});

// POST /api/history
// Save a new chat or update an existing chat
router.post('/', async (req, res) => {
    try {
        const { userId, chatData } = req.body;

        if (!userId || !chatData || !chatData.id) {
            return res.status(400).json({
                success: false,
                error: 'userId and chatData (containing id) are required in the request body'
            });
        }

        const result = await historyService.saveOrUpdateChat(userId, chatData);
        res.status(200).json({ success: true, data: result });
    } catch (error) {
        console.error('Error saving/updating chat:', error);
        res.status(500).json({ success: false, error: 'Internal server error while saving history' });
    }
});

export default router;
