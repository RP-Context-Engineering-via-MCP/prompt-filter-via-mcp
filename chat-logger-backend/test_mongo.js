import mongoose from 'mongoose';

async function runTests() {
    console.log('Starting MongoDB raw connection test...');
    
    const uri = 'mongodb://admin:admin@ac-fmezbdg-shard-00-00.mll4qqh.mongodb.net:27017,ac-fmezbdg-shard-00-01.mll4qqh.mongodb.net:27017,ac-fmezbdg-shard-00-02.mll4qqh.mongodb.net:27017/?ssl=true&replicaSet=atlas-9xyre9-shard-0&authSource=admin&retryWrites=true&w=majority&appName=PRchatHistory';
    
    try {
        await mongoose.connect(uri, { serverSelectionTimeoutMS: 5000 });
        console.log(`✅ SUCCESS: Connected natively without SRV records!`);
        await mongoose.disconnect();
    } catch (e) {
        console.error(`❌ ERROR: Could not connect natively.`);
        console.error('Details:', e.message);
    }
    process.exit(0);
}

runTests();
