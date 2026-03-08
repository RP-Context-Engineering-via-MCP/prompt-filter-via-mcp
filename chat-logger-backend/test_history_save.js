async function testHistorySave() {
    try {
        const response = await fetch('http://localhost:3005/api/history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: 'testUser',
                chatData: {
                    id: `test-history-chat-${Date.now()}`,
                    title: 'Test web-client chat',
                    model: 'chatgpt',
                    messages: [
                        { role: 'user', content: 'test message' }
                    ]
                }
            })
        });

        const data = await response.json();
        console.log('Response from server:', JSON.stringify(data, null, 2));
    } catch (error) {
        console.error('Error during test:', error);
    }
}

testHistorySave();
