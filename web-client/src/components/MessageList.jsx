import React, { useEffect, useRef } from 'react';
import Message from './Message';

const MessageList = ({ messages, selectedModel }) => {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const getModelBadge = (model) => {
        if (model === 'chatgpt') {
            return (
                <div className="flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm font-medium border border-green-200 mb-4">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    ChatGPT
                </div>
            );
        }
        if (model === 'claude') {
            return (
                <div className="flex items-center gap-2 bg-orange-50 text-orange-700 px-3 py-1 rounded-full text-sm font-medium border border-orange-200 mb-4">
                    <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                    Claude
                </div>
            );
        }
        return null;
    };

    return (
        <div className="flex-1 overflow-y-auto px-4 md:px-0 py-6">
            <div className="max-w-3xl mx-auto">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-stone-500">
                        {selectedModel && getModelBadge(selectedModel)}
                        <h2 className="font-serif text-3xl text-stone-700 mb-2">Welcome</h2>
                        <p>How can I help you today?</p>
                    </div>
                ) : (
                    messages.map((msg, index) => (
                        <Message key={index} role={msg.role} content={msg.content} />
                    ))
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default MessageList;
