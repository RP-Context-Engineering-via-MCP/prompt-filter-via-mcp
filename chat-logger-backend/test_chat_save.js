async function testSave() {
    try {
        const response = await fetch('http://localhost:3005/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                selected_session_id: 'test-session-123',
                user_id: 'test-user-456',
                session_id: 'test-chat-session-789',
                source: 'test-source',
                user_prompt: 'Hello, this is a test prompt',
                llm_response: 'This is a test response from the LLM',
                metadata: {
                    url: 'http://test.url'
                }
            })
        });

        const data = await response.json();
        console.log('Response from server:', data);
    } catch (error) {
        console.error('Error during test:', error);
    }
}

testSave();
