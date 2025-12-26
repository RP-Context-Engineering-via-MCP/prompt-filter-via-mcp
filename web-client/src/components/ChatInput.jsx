import React, { useState, useRef, useEffect } from 'react';

const ChatInput = ({ onSend, disabled }) => {
    const [input, setInput] = useState('');
    const textareaRef = useRef(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSend(input);
            setInput('');
            // Reset height
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleChange = (e) => {
        setInput(e.target.value);
        // Auto-resize
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    };

    return (
        <div className="w-full bg-white border-t border-gray-200 py-4 pb-6 px-4 md:px-0">
            <div className="max-w-3xl mx-auto">
                <form onSubmit={handleSubmit} className="relative">
                    <div className="relative flex items-end border border-gray-300 bg-white rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-primary-light focus-within:border-primary-light overflow-hidden transition-all duration-200">
                        <textarea
                            ref={textareaRef}
                            rows={1}
                            value={input}
                            onChange={handleChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Message Memora..."
                            className="w-full py-3 pl-4 pr-12 bg-transparent border-none focus:ring-0 resize-none text-black placeholder-gray-400 max-h-[200px]"
                            disabled={disabled}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || disabled}
                            className={`absolute right-2 bottom-2 p-1.5 rounded-lg transition-colors ${input.trim() && !disabled
                                ? 'bg-primary text-white hover:bg-primary-hover'
                                : 'bg-gray-100 text-gray-300 cursor-not-allowed'
                                }`}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                                <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.519 60.519 0 003.478 2.404z" />
                            </svg>
                        </button>
                    </div>
                    <div className="mt-2 text-center">
                        <p className="text-xs text-stone-400">
                            AI can make mistakes. Please use with discretion.
                        </p>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ChatInput;
