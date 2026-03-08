import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import LLMSelectionModal from './LLMSelectionModal';
import Sidebar from './Sidebar';
import Header from './Header';
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const ChatLayout = () => {
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [isLLMModalOpen, setIsLLMModalOpen] = useState(false);
    const [selectedModel, setSelectedModel] = useState(null);
    const [chatHistory, setChatHistory] = useState([]);
    const [currentChatId, setCurrentChatId] = useState(null);
    const [filterEnabled, setFilterEnabled] = useState(true); // Default to ON
    const [sessionContext, setSessionContext] = useState(null); // Default to no session
    const clientRef = useRef(null);

    // Load history and session context on mount
    useEffect(() => {
        // TODO: add jwt token support for user authentication
        const userId = localStorage.getItem('userId') || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2';

        const fetchHistory = async () => {
            try {
                const response = await fetch(`http://localhost:3005/api/history/${userId}`);
                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.data) {
                        setChatHistory(result.data);
                    }
                }
            } catch (error) {
                console.error("Failed to fetch chat history:", error);
            }
        };

        fetchHistory();

        const savedSession = localStorage.getItem('sessionContext');
        if (savedSession) {
            setSessionContext(JSON.parse(savedSession));
        }
    }, []);

    // Optional: Keep sessionStorage as a fallback backup or remove it entirely.
    // We will rely on the backend for persistence now.

    // Save session context whenever it changes
    useEffect(() => {
        if (sessionContext) {
            localStorage.setItem('sessionContext', JSON.stringify(sessionContext));
        } else {
            localStorage.removeItem('sessionContext');
        }
    }, [sessionContext]);

    // Initialize MCP Client
    useEffect(() => {
        const initClient = async () => {
            try {
                const transport = new SSEClientTransport(new URL("http://localhost:3001/sse"));
                const client = new Client(
                    { name: "chat-client", version: "1.0.0" },
                    { capabilities: {} }
                );
                await client.connect(transport);
                clientRef.current = client;
                console.log("Connected to MCP Server");
            } catch (error) {
                console.error("Failed to connect to MCP Server", error);
            }
        };
        initClient();
    }, []);

    const handleSend = async (text) => {
        setIsTyping(true);

        // Add initial user message
        const baseUserMsg = { role: 'user', content: text };
        let currentMessages = [...messages, baseUserMsg];
        setMessages(currentMessages);

        // Update Persistence (Initial User Prompt)
        let chatId = currentChatId;
        if (!chatId) {
            chatId = Date.now().toString();
            setCurrentChatId(chatId);
        }

        const createChatEntry = (msgList) => ({
            id: chatId,
            title: msgList.length === 1 ? text.slice(0, 30) + (text.length > 30 ? '...' : '') : 'New Chat',
            date: new Date().toISOString(),
            model: selectedModel || 'chatgpt',
            messages: msgList
        });

        // Save initial state to history
        setChatHistory(prev => {
            const existingIndex = prev.findIndex(c => c.id === chatId);
            let newHistory;
            if (existingIndex >= 0) {
                newHistory = [...prev];
                newHistory[existingIndex] = { ...newHistory[existingIndex], messages: currentMessages };
            } else {
                newHistory = [createChatEntry(currentMessages), ...prev];
            }
            saveChatToBackend(chatId, newHistory.find(c => c.id === chatId));
            return newHistory;
        });

        let finalPromptForMCP = text;
        let pfeData = null;

        try {
            // Step 1: Pass through Prompt Filter Engine first (if enabled)
            if (filterEnabled) {
                try {
                    const filterResponse = await fetch('http://localhost:3003/filter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: text })
                    });

                    if (filterResponse.ok) {
                        pfeData = await filterResponse.json();
                        finalPromptForMCP = pfeData.redacted;

                        // Instantly update the user message with secured prompt
                        const securedUserMsg = { ...baseUserMsg, securedPrompt: pfeData.redacted };
                        currentMessages = [...messages, securedUserMsg];
                        setMessages(currentMessages);

                        // Save updated user message
                        setChatHistory(prev => {
                            const existingIndex = prev.findIndex(c => c.id === chatId);
                            if (existingIndex >= 0) {
                                const newHistory = [...prev];
                                newHistory[existingIndex] = { ...newHistory[existingIndex], messages: currentMessages };
                                saveChatToBackend(chatId, newHistory[existingIndex]);
                                return newHistory;
                            }
                            return prev;
                        });
                    } else {
                        console.error('PFE error:', await filterResponse.text());
                    }
                } catch (pfeErr) {
                    console.error('Failed to reach PFE:', pfeErr);
                }
            }

            if (!clientRef.current) {
                throw new Error("MCP Client not connected");
            }

            // Step 2: Call the MCP tool with the secured Prompt
            const result = await clientRef.current.callTool({
                name: "process_prompt",
                arguments: {
                    prompt: finalPromptForMCP,
                    enable_filter: false, // MCP no longer handles filtering
                    source: "web_client"  // web_client mode: enrichment service calls OpenAI API
                }
            });

            const responseTextRaw = result.content[0].text;
            let displayResponse = responseTextRaw;

            // Step 3: Parse the JSON from MCP
            try {
                const parsedResponse = JSON.parse(responseTextRaw);
                if (parsedResponse.error) {
                    displayResponse = parsedResponse.error;
                } else {
                    displayResponse = parsedResponse.llm_response;
                }
            } catch (jsonErr) {
                // If it fails to parse (e.g., unexpected error string), just show raw
                console.warn('Failed to parse MCP response as JSON:', jsonErr);
            }

            const aiResponse = {
                role: 'assistant',
                content: displayResponse
            };
            const finalMessages = [...currentMessages, aiResponse];
            setMessages(finalMessages);

            // Update Persistence with AI response
            setChatHistory(prev => {
                const existingIndex = prev.findIndex(c => c.id === chatId);
                if (existingIndex >= 0) {
                    const newHistory = [...prev];
                    newHistory[existingIndex] = { ...newHistory[existingIndex], messages: finalMessages };

                    // Persist AI response to backend asynchronously
                    saveChatToBackend(chatId, newHistory[existingIndex]);
                    return newHistory;
                }
                return prev;
            });


        } catch (error) {
            console.error("Error sending message:", error);
            const errorResponse = {
                role: 'assistant',
                content: "Sorry, I couldn't reach the server. Please check the console."
            };
            setMessages(prev => [...prev, errorResponse]);
        } finally {
            setIsTyping(false);
        }
    };

    const saveChatToBackend = async (chatId, chatData) => {
        const userId = localStorage.getItem('userId') || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2'; // Hardcoded user id fallback
        try {
            await fetch('http://localhost:3005/api/history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ userId, chatData })
            });
        } catch (error) {
            console.error("Failed to save chat to backend:", error);
        }
    };

    const handleStartConversation = (model) => {
        setMessages([]); // Reset to Welcome screen
        setSelectedModel(model);
        setCurrentChatId(null); // Reset ID so a new one is generated on first message
        setIsLLMModalOpen(false);
    };

    const loadChat = (chat) => {
        setMessages(chat.messages);
        setSelectedModel(chat.model);
        setCurrentChatId(chat.id);
    };

    const handleNewChat = () => {
        setIsLLMModalOpen(true);
    };

    return (
        <div className="flex h-screen bg-memora-bg font-sans overflow-hidden selection:bg-indigo-100 selection:text-indigo-900">
            <Sidebar
                chatHistory={chatHistory}
                currentChatId={currentChatId}
                onLoadChat={loadChat}
                onNewChat={handleNewChat}
            />

            <main className="flex-1 flex flex-col h-full relative w-full max-w-[1600px] mx-auto">
                <Header
                    selectedModel={selectedModel}
                    sessionContext={sessionContext}
                    onSessionContextChange={setSessionContext}
                />

                {/* Main Content Area - mimicking "Session Contexts" look but for active chat */}
                <div className="flex-1 px-6 pb-6 min-h-0">
                    <div className="h-full bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col overflow-hidden">
                        {/* Chat Header inside card if needed, or just cleaner layout */}

                        {/* Mobile Header Toggle (simplified) */}
                        <header className="md:hidden flex items-center justify-between p-4 border-b border-gray-100 bg-white">
                            <div className="font-bold text-lg text-slate-800">Memora</div>
                            <button className="p-2 text-stone-500 hover:bg-stone-100 rounded-lg">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                                </svg>
                            </button>
                        </header>

                        <MessageList messages={messages} selectedModel={selectedModel} />

                        <div className="bg-white border-t border-slate-100">
                            <ChatInput
                                onSend={handleSend}
                                disabled={isTyping}
                                filterEnabled={filterEnabled}
                                onToggleFilter={() => setFilterEnabled(!filterEnabled)}
                            />
                        </div>
                    </div>
                </div>
            </main>

            <LLMSelectionModal
                isOpen={isLLMModalOpen}
                onClose={() => setIsLLMModalOpen(false)}
                onConfirm={handleStartConversation}
            />
        </div>
    );
};

export default ChatLayout;
