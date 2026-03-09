import { Router } from 'express';
import { ChatLog } from '../models/db.js';
import { checkAndTriggerCondensation, triggerCondensation } from '../services/contextManagerService.js';

const router = Router();

// POST /api/chats — Save a new chat log
router.post('/', async (req, res) => {
    try {
        let { session_id, source, user_prompt, llm_response, metadata, selected_session_id, user_id } = req.body;

        const effectiveUserId = user_id || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2';

        if (!selected_session_id) {
            try {
                const userManagerUrl = process.env.USER_MANAGER_URL || 'http://host.docker.internal:8080';
                console.log(`[chatRoutes DEBUG] Fetching current session for ${effectiveUserId} from ${userManagerUrl}/api/users/${effectiveUserId}/current-session`);
                const sessionRes = await fetch(`${userManagerUrl}/api/users/${effectiveUserId}/current-session`);
                console.log(`[chatRoutes DEBUG] Fetch response status: ${sessionRes.status}`);
                if (sessionRes.ok) {
                    const sessionData = await sessionRes.json();
                    console.log(`[chatRoutes DEBUG] Fetch response data:`, sessionData);
                    if (sessionData.current_session_id) {
                        selected_session_id = sessionData.current_session_id;
                        console.log(`[chatRoutes DEBUG] Set selected_session_id to ${selected_session_id}`);
                    }
                } else {
                    console.log(`[chatRoutes DEBUG] Fetch not ok. Body:`, await sessionRes.text());
                }
            } catch (err) {
                console.error(`[chatRoutes] Failed to fetch current session for user ${effectiveUserId}:`, err.message);
            }
        }

        console.log(`[chatRoutes DEBUG] Final selected_session_id before save:`, selected_session_id);

        if (!user_prompt || !llm_response) {
            return res.status(400).json({
                error: 'user_prompt and llm_response are required'
            });
        }

        const chatLog = new ChatLog({
            session_id,
            selected_session_id,
            user_id: effectiveUserId,
            source,
            user_prompt,
            llm_response,
            metadata: {
                url: metadata?.url,
                model: metadata?.model
            }
        });

        const saved = await chatLog.save();
        console.info(`[INFO] Chat log saved successfully. ID: ${saved._id}, User: ${effectiveUserId}, AppSession: ${selected_session_id || 'N/A'}`);
        res.status(201).json(saved);

        // Check if condensation should be triggered
        checkAndTriggerCondensation(session_id, user_prompt, llm_response);
    } catch (error) {
        console.error('Error saving chat log:', error);
        res.status(500).json({ error: 'Failed to save chat log' });
    }
});

// GET /api/chats — Retrieve chat logs with optional filters
// Supports: session_id, source, user_id, selected_session_id, skip, limit
router.get('/', async (req, res) => {
    try {
        const { session_id, source, user_id, selected_session_id, skip = 0, limit = 50 } = req.query;

        const filter = {};
        if (session_id) filter.session_id = session_id;
        if (source) filter.source = source;
        if (user_id) filter.user_id = user_id;
        if (selected_session_id) filter.selected_session_id = selected_session_id;

        console.info(`[INFO] GET /api/chats | Filters: user_id=${user_id || 'N/A'}, selected_session_id=${selected_session_id || 'N/A'}, session_id=${session_id || 'N/A'}, source=${source || 'N/A'}, skip=${skip}, limit=${limit}`);

        const sortOrder = req.query.sort_desc === 'true' ? -1 : 1;

        const chats = await ChatLog.find(filter)
            .sort({ timestamp: sortOrder })  // chronological order (oldest first) if 1, newest if -1
            .skip(parseInt(skip))
            .limit(parseInt(limit));

        console.info(`[INFO] GET /api/chats | Found ${chats.length} chat logs matching filters`);
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

// GET /api/chats/test-condense — Retrieve a single chat log by ID
router.get('/test-condense/:session_id', async (req, res) => {
    try {
        await triggerCondensation(req.params.session_id);
        res.json({ message: 'Triggered condensation for ' + req.params.session_id });
    } catch (error) {
        console.error('Error triggering condensation manually:', error);
        res.status(500).json({ error: 'Failed to trigger condensation manually: ' + error.message });
    }
});

export default router;
