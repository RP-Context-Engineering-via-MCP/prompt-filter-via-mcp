import React, { useEffect, useRef } from 'react';
import Message from './Message';

const ModelBadge = ({ model }) => {
    if (model === 'chatgpt') return (
        <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-full text-xs font-bold border border-emerald-200 mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
            Connected to ChatGPT
        </div>
    );
    if (model === 'claude') return (
        <div className="flex items-center gap-2 bg-orange-50 text-orange-700 px-3 py-1.5 rounded-full text-xs font-bold border border-orange-200 mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></div>
            Connected to Claude
        </div>
    );
    return null;
};

const EmptyState = ({ selectedModel }) => (
    <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center">
        {/* Shield Icon */}
        <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-3xl flex items-center justify-center shadow-indigo-lg mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-10 h-10 text-white">
                <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08z" clipRule="evenodd" />
            </svg>
        </div>

        {/* Heading */}
        <h2 className="text-2xl font-bold text-slate-800 tracking-tight mb-2">
            Memora Enterprise Shield
        </h2>
        <p className="text-sm text-slate-500 max-w-xs leading-relaxed mb-8">
            Your AI conversations are protected with advanced prompt filtering and context enrichment.
        </p>

        {/* Model badge if selected */}
        {selectedModel && <ModelBadge model={selectedModel} />}

        {/* Feature Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2">
            {[
                { label: 'Prompt Filtering', icon: '🔒' },
                { label: 'Context Aware', icon: '🧠' },
                { label: 'Multi-Model', icon: '⚡' },
            ].map((f) => (
                <div key={f.label} className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs font-semibold text-slate-600 shadow-sm">
                    <span>{f.icon}</span>
                    {f.label}
                </div>
            ))}
        </div>
    </div>
);

const MessageList = ({ messages, selectedModel }) => {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto message-scrollbar">
            <div className="max-w-3xl mx-auto px-6 py-6 h-full flex flex-col">
                {messages.length === 0 ? (
                    <EmptyState selectedModel={selectedModel} />
                ) : (
                    <>
                        {/* Model badge at top of conversation */}
                        {selectedModel && (
                            <div className="flex justify-center mb-6">
                                <ModelBadge model={selectedModel} />
                            </div>
                        )}
                        {messages.map((msg, index) => (
                            <Message
                                key={index}
                                role={msg.role}
                                content={msg.content}
                                securedPrompt={msg.securedPrompt}
                            />
                        ))}
                    </>
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default MessageList;
