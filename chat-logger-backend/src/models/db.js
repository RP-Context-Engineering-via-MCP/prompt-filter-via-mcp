import mongoose from 'mongoose';

const MONGO_URI = process.env.MONGO_URI;

export async function connectDB() {
    try {
        await mongoose.connect(MONGO_URI);
        console.error("Successfully connected to MongoDB");
    } catch (error) {
        console.error("Error connecting to MongoDB:", error);
        // Do not exit the process, let the server continue running even if DB fails initially
    }
}

const chatLogSchema = new mongoose.Schema({
    session_id: { type: String, required: false },
    selected_session_id: { type: String, required: false },
    user_id: { type: String, required: false },
    source: { type: String, required: false },
    user_prompt: { type: String, required: true },
    llm_response: { type: String, required: true },
    metadata: {
        url: { type: String, required: false },
        model: { type: String, required: false }
    },
    timestamp: { type: Date, default: Date.now }
});

export const ChatLog = mongoose.model('ChatLog', chatLogSchema);
