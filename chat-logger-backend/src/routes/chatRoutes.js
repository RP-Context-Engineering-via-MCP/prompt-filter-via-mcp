import { Router } from 'express';
import { ChatLog } from '../models/db.js';

const router = Router();

// POST /api/chats — Save a new chat log
router.post('/', async (req, res) => {
    try {
        const { session_id, source, user_prompt, llm_response, metadata } = req.body;

        if (!user_prompt || !llm_response) {
            return res.status(400).json({
                error: 'user_prompt and llm_response are required'
            });
        }

        const chatLog = new ChatLog({
            session_id,
            source,
            user_prompt,
            llm_response,
            metadata: {
                url: metadata?.url,
                model: metadata?.model
            }
        });

        const saved = await chatLog.save();
        res.status(201).json(saved);
    } catch (error) {
        console.error('Error saving chat log:', error);
        res.status(500).json({ error: 'Failed to save chat log' });
    }
});

// GET /api/chats — Retrieve chat logs with optional filters
router.get('/', async (req, res) => {
    try {
        const { session_id, source, limit = 50 } = req.query;

        const filter = {};
        if (session_id) filter.session_id = session_id;
        if (source) filter.source = source;

        const chats = await ChatLog.find(filter)
            .sort({ timestamp: -1 })
            .limit(parseInt(limit));

        res.json(chats);
    } catch (error) {
        console.error('Error retrieving chat logs:', error);
        res.status(500).json({ error: 'Failed to retrieve chat logs' });
    }
});

// GET /api/chats/:id — Retrieve a single chat log by ID
router.get('/:id', async (req, res) => {
    try {
        const chatLog = await ChatLog.findById(req.params.id);
        if (!chatLog) {
            return res.status(404).json({ error: 'Chat log not found' });
        }
        res.json(chatLog);
    } catch (error) {
        console.error('Error retrieving chat log:', error);
        res.status(500).json({ error: 'Failed to retrieve chat log' });
    }
});

export default router;
