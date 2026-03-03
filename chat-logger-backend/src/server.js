import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { connectDB } from './models/db.js';
import chatRoutes from './routes/chatRoutes.js';

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/chats', chatRoutes);

// Health check
app.get('/', (req, res) => {
    res.json({ status: 'ok', service: 'chat-logger-backend' });
});

// Start server
const PORT = process.env.PORT || 3005;

connectDB().then(() => {
    app.listen(PORT, () => {
        console.log(`Chat Logger Backend running on port ${PORT}`);
    });
});
