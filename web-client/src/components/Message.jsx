import React, { useState } from 'react';

const Message = ({ role, content, securedPrompt }) => {
    const isUser = role === 'user';
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div className={`flex w-full gap-3 mb-5 ${isUser ? 'justify-end' : 'justify-start'}`}>

            {/* Assistant Avatar */}
            {!isUser && (
                <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-indigo-sm mt-0.5">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-white">
                        <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08z" clipRule="evenodd" />
                    </svg>
                </div>
            )}

            {/* Message Content */}
            <div className={`flex flex-col max-w-[78%] md:max-w-[68%] ${isUser ? 'items-end' : 'items-start'}`}>
                {/* Role Label */}
                <div className={`text-[10px] font-bold uppercase tracking-widest mb-1.5 ${isUser ? 'text-slate-400' : 'text-indigo-400'}`}>
                    {isUser ? 'You' : 'Memora AI'}
                </div>

                {/* Bubble */}
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    isUser
                        ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-sm shadow-indigo-md'
                        : 'bg-white text-slate-800 border border-slate-100 shadow-sm rounded-tl-sm'
                }`}>
                    <div className="whitespace-pre-wrap break-words">{content}</div>
                </div>

                {/* Secured Prompt Reveal */}
                {isUser && securedPrompt && (
                    <div className="mt-1.5 w-full flex flex-col items-end">
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400 hover:text-indigo-500 transition-colors py-0.5"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                            </svg>
                            <span>Secured prompt</span>
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                className={`w-3 h-3 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                            >
                                <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clipRule="evenodd" />
                            </svg>
                        </button>

                        {isExpanded && (
                            <div className="mt-1 w-full p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-xs text-indigo-700 break-words whitespace-pre-wrap animate-slide-up">
                                <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold text-indigo-400 uppercase tracking-widest">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                                    </svg>
                                    Prompt Shield — Redacted
                                </div>
                                {securedPrompt}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* User Avatar */}
            {isUser && (
                <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center shadow-sm mt-0.5">
                    <span className="text-white text-[10px] font-bold">AR</span>
                </div>
            )}
        </div>
    );
};

export default Message;
