import React, { useEffect, useRef } from 'react';
import Message from './Message';

const MessageList = ({ messages }) => {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto px-4 md:px-0 py-6">
            <div className="max-w-3xl mx-auto">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-stone-500">
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
