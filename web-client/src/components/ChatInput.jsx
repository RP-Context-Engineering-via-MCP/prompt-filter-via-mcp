import React, { useState, useRef } from 'react';

const ChatInput = ({ onSend, disabled, filterEnabled, onToggleFilter }) => {
    const [input, setInput] = useState('');
    const textareaRef = useRef(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSend(input);
            setInput('');
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
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    };

    return (
        <div className="w-full bg-white border-t border-slate-100 px-6 pt-4 pb-5">
            <div className="max-w-3xl mx-auto space-y-3">

                {/* Prompt Shield Toggle */}
                <div className="flex items-center justify-between">
                    <label className="inline-flex items-center gap-3 cursor-pointer group">
                        <div className="relative">
                            <input
                                type="checkbox"
                                className="sr-only peer"
                                checked={filterEnabled}
                                onChange={onToggleFilter}
                                disabled={disabled}
                            />
                            {/* Track */}
                            <div className="w-10 h-5 bg-slate-200 peer-checked:bg-indigo-600 rounded-full transition-colors duration-200 peer-focus:ring-2 peer-focus:ring-indigo-300 peer-disabled:opacity-50"></div>
                            {/* Thumb */}
                            <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200 peer-checked:translate-x-5"></div>
                        </div>

                        <div className="flex items-center gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={`w-3.5 h-3.5 transition-colors ${filterEnabled ? 'text-indigo-500' : 'text-slate-400'}`}>
                                <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08z" clipRule="evenodd" />
                            </svg>
                            <span className={`text-xs font-semibold transition-colors ${filterEnabled ? 'text-slate-700' : 'text-slate-400'}`}>
                                Prompt Shield
                            </span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border transition-all ${
                                filterEnabled
                                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                                    : 'bg-slate-100 text-slate-400 border-slate-200'
                            }`}>
                                {filterEnabled ? 'ACTIVE' : 'OFF'}
                            </span>
                        </div>
                    </label>

                    <span className="text-[10px] text-slate-400 font-medium hidden sm:block">
                        Enter to send · Shift+Enter for new line
                    </span>
                </div>

                {/* Input Container */}
                <form onSubmit={handleSubmit}>
                    <div className={`relative flex items-end bg-slate-50 border rounded-2xl overflow-hidden transition-all duration-200 ${
                        disabled
                            ? 'border-slate-200 opacity-80'
                            : 'border-slate-200 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 focus-within:bg-white'
                    }`}>
                        <textarea
                            ref={textareaRef}
                            rows={1}
                            value={input}
                            onChange={handleChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Message Memora..."
                            disabled={disabled}
                            className="flex-1 py-3.5 pl-4 pr-14 bg-transparent border-none focus:ring-0 resize-none text-sm text-slate-800 placeholder-slate-400 max-h-[200px] leading-relaxed"
                        />

                        {/* Send Button */}
                        <button
                            type="submit"
                            disabled={!input.trim() || disabled}
                            className={`absolute right-2.5 bottom-2.5 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 flex-shrink-0 ${
                                input.trim() && !disabled
                                    ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-indigo-sm hover:shadow-indigo-md hover:from-indigo-500 hover:to-indigo-600'
                                    : disabled
                                        ? 'bg-indigo-500 text-white cursor-not-allowed'
                                        : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                            }`}
                        >
                            {disabled ? (
                                <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                            ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                                    <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.519 60.519 0 003.478 2.404z" />
                                </svg>
                            )}
                        </button>
                    </div>

                    <p className="mt-2 text-center text-[11px] text-slate-400 font-medium">
                        Memora AI can make mistakes. Use with discretion.
                    </p>
                </form>
            </div>
        </div>
    );
};

export default ChatInput;
