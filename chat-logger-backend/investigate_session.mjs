import mongoose from 'mongoose';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config({ path: join(__dirname, '.env') });

import { checkAndTriggerCondensation } from './src/services/contextManagerService.js';
import { ChatLog } from './src/models/db.js';

async function investigate() {
    try {
        await mongoose.connect(process.env.MONGO_URI);
        console.log('Connected to MongoDB');

        const session_id = "c8cd2096-30ad-4aa5-a318-409bd35b7f68";
        const count = await ChatLog.countDocuments({ session_id });
        console.log(`\n--- Investigation for Session: ${session_id} ---`);
        console.log(`Document count: ${count}`);

        const logs = await ChatLog.find({ session_id }).sort({ timestamp: -1 });
        console.log(`\nDocument details (${logs.length} found):`);
        logs.forEach((l, i) => {
            console.log(`${i + 1}. [${l.timestamp}] Prompt: "${l.user_prompt.substring(0, 30)}..." | Response: "${l.llm_response.substring(0, 30)}..."`);
        });

        console.log(`\n--- Triggering Condensation Manually ---`);
        console.log(`Running checkAndTriggerCondensation...`);
        await checkAndTriggerCondensation(session_id);
    } catch (err) {
        console.error('Error during investigation:', err);
    } finally {
        setTimeout(() => process.exit(0), 3000); // give triggerCondensation time to finish
    }
}

investigate();
