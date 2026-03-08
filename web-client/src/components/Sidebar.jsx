import React from 'react';

const Sidebar = ({ chatHistory, currentChatId, onLoadChat, onNewChat }) => {
    return (
        <aside className="hidden md:flex flex-col w-[272px] bg-white border-r border-slate-100 shadow-sm z-20 flex-shrink-0">

            {/* Brand */}
            <div className="px-6 pt-7 pb-5 border-b border-slate-100">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-xl flex items-center justify-center shadow-indigo-md flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-white">
                            <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08zM12 19.34c-2.313-.4-6-3.237-6-8.59 0-.84.092-1.648.261-2.421 2.316.516 4.795.556 7.151.13.78 1.602 1.305 3.323 1.54 5.093A13.754 13.754 0 0112 19.34z" clipRule="evenodd" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="font-bold text-lg text-slate-900 tracking-tight leading-none">Memora</h1>
                        <p className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest mt-0.5">Enterprise Shield</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 flex flex-col px-4 py-5 min-h-0 overflow-hidden">

                {/* Session History Nav Item */}
                <div className="relative flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-xl shadow-indigo-md mb-5 cursor-pointer select-none">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white/5 rounded-xl" />
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 flex-shrink-0">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-semibold">Session History</span>
                    <div className="ml-auto w-1.5 h-1.5 bg-white/70 rounded-full" />
                </div>

                {/* Chat History Section */}
                <div className="flex-1 min-h-0 flex flex-col">
                    <div className="flex items-center justify-between mb-3 px-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Recent Chats</span>
                    </div>

                    {/* New Chat Button */}
                    <button
                        onClick={onNewChat}
                        className="flex items-center gap-2.5 px-3 py-2.5 mb-2 text-sm text-indigo-600 font-semibold hover:bg-primary-subtle rounded-xl cursor-pointer transition-all duration-200 group border border-dashed border-indigo-200 hover:border-indigo-300"
                    >
                        <div className="w-5 h-5 rounded-lg bg-indigo-100 flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-3 h-3 text-indigo-600">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                            </svg>
                        </div>
                        New Conversation
                    </button>

                    {/* Chat History List */}
                    <div className="flex-1 overflow-y-auto space-y-0.5 sidebar-scrollbar pr-1">
                        {chatHistory.length === 0 ? (
                            <div className="px-3 py-6 text-center">
                                <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-slate-400">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                                    </svg>
                                </div>
                                <p className="text-xs text-slate-400 font-medium">No conversations yet</p>
                            </div>
                        ) : (
                            chatHistory.map((chat) => (
                                <button
                                    key={chat.id}
                                    onClick={() => onLoadChat(chat)}
                                    className={`w-full text-left px-3 py-2.5 rounded-xl flex items-center gap-2.5 text-sm transition-all duration-150 group ${
                                        currentChatId === chat.id
                                            ? 'bg-primary-subtle text-indigo-700 font-semibold'
                                            : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                                    }`}
                                >
                                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors ${
                                        currentChatId === chat.id ? 'bg-indigo-500' : 'bg-slate-300 group-hover:bg-slate-400'
                                    }`} />
                                    <span className="truncate">{chat.title || 'New Chat'}</span>
                                </button>
                            ))
                        )}
                    </div>
                </div>
            </nav>

            {/* Security Status Footer */}
            <div className="px-4 pb-5 pt-4 border-t border-slate-100 space-y-3">
                {/* Protected Status Badge */}
                <div className="flex items-center gap-2.5 px-3 py-2.5 bg-emerald-50 rounded-xl border border-emerald-100">
                    <div className="relative flex-shrink-0">
                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                        <div className="absolute inset-0 w-2 h-2 rounded-full bg-emerald-400 animate-ping opacity-75"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold text-emerald-700">Prompt Shield Active</p>
                        <p className="text-[10px] text-emerald-600 font-medium">All prompts are secured</p>
                    </div>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-emerald-500 flex-shrink-0">
                        <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08z" clipRule="evenodd" />
                    </svg>
                </div>

                {/* Storage Capacity */}
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-semibold text-slate-500">Storage</span>
                        <span className="text-[11px] font-bold text-indigo-600">78%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-1.5 rounded-full" style={{ width: '78%' }}></div>
                    </div>
                    <div className="mt-1.5 text-[10px] text-slate-400 font-medium">1.2 GB of 1.5 GB used</div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
