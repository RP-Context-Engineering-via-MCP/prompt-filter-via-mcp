import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import LLMSelectionModal from './LLMSelectionModal';
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
    const clientRef = useRef(null);

    // Load history on mount
    useEffect(() => {
        const savedHistory = localStorage.getItem('chatHistory');
        if (savedHistory) {
            setChatHistory(JSON.parse(savedHistory));
        }
    }, []);

    // Save history whenever it changes
    useEffect(() => {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }, [chatHistory]);

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
        // Add user message
        const userMsg = { role: 'user', content: text };
        const updatedMessages = [...messages, userMsg];
        setMessages(updatedMessages);

        // Update Persistence
        let chatId = currentChatId;
        if (!chatId) {
            chatId = Date.now().toString();
            setCurrentChatId(chatId);
        }

        const newChatEntry = {
            id: chatId,
            title: messages.length === 0 ? text.slice(0, 30) + (text.length > 30 ? '...' : '') : 'New Chat',
            date: new Date().toISOString(),
            model: selectedModel || 'chatgpt', // Default fallback
            messages: updatedMessages
        };

        setChatHistory(prev => {
            const existingIndex = prev.findIndex(c => c.id === chatId);
            if (existingIndex >= 0) {
                const newHistory = [...prev];
                newHistory[existingIndex] = { ...newHistory[existingIndex], messages: updatedMessages };
                return newHistory;
            } else {
                return [newChatEntry, ...prev];
            }
        });

        setIsTyping(true);

        try {
            if (!clientRef.current) {
                throw new Error("MCP Client not connected");
            }

            // Call the MCP tool
            const result = await clientRef.current.callTool({
                name: "process_prompt",
                arguments: {
                    prompt: text,
                    enable_filter: filterEnabled
                }
            });

            // Extract text from result content
            const responseText = result.content[0].text;

            const aiResponse = {
                role: 'assistant',
                content: responseText
            };
            const finalMessages = [...updatedMessages, aiResponse];
            setMessages(finalMessages);

            // Update Persistence with AI response
            setChatHistory(prev => {
                const existingIndex = prev.findIndex(c => c.id === chatId);
                if (existingIndex >= 0) {
                    const newHistory = [...prev];
                    newHistory[existingIndex] = { ...newHistory[existingIndex], messages: finalMessages };
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

    return (
        <div className="flex h-screen bg-white font-sans text-black">
            {/* Sidebar - Hidden on mobile for simplicity, or could be a drawer */}
            <aside className="hidden md:flex flex-col w-[260px] bg-gray-50 border-r border-gray-200 p-4">
                <div className="flex items-center gap-2 px-2 py-3 mb-6">
                    <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center text-white font-serif font-bold cursor-pointer">M</div>
                    <span className="font-serif font-semibold text-lg cursor-pointer">Memora</span>
                </div>

                <button
                    onClick={() => setIsLLMModalOpen(true)}
                    className="flex items-center gap-2 w-full px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors text-sm font-medium mb-4"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                    New chat
                </button>

                <div className="flex-1 overflow-y-auto">
                    <div className="px-2 text-xs font-medium text-stone-500 mb-2">Recent</div>
                    {chatHistory.map((chat) => (
                        <div
                            key={chat.id}
                            onClick={() => loadChat(chat)}
                            className={`px-3 py-2 rounded-lg hover:bg-stone-200/50 cursor-pointer text-sm truncate text-stone-600 ${currentChatId === chat.id ? 'bg-stone-200' : ''}`}
                        >
                            {chat.title || 'New Chat'}
                        </div>
                    ))}
                    {chatHistory.length === 0 && (
                        <div className="px-3 py-2 text-sm text-stone-400 italic">No recent chats</div>
                    )}
                </div>

                <div className="mt-auto px-2 py-3 text-sm text-stone-500 border-t border-stone-200/50 flex items-center gap-2 cursor-pointer hover:text-stone-700">
                    <div className="w-6 h-6 rounded-full bg-stone-300"></div>
                    User Account
                </div>
            </aside>

            <main className="flex-1 flex flex-col h-full relative">
                <header className="md:hidden flex items-center justify-between p-4 border-b border-gray-200 bg-white z-10">
                    <div className="font-serif font-semibold text-lg">Memora</div>
                    <button className="p-2 text-stone-500">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                        </svg>
                    </button>
                </header>

                <MessageList messages={messages} selectedModel={selectedModel} />
                <ChatInput
                    onSend={handleSend}
                    disabled={isTyping}
                    filterEnabled={filterEnabled}
                    onToggleFilter={() => setFilterEnabled(!filterEnabled)}
                />
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
