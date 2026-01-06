import React from 'react';

const Sidebar = ({ chatHistory, currentChatId, onLoadChat, onNewChat }) => {
    return (
        <aside className="hidden md:flex flex-col w-[280px] bg-white border-r border-gray-100 p-6 shadow-sm z-20">
            {/* Brand */}
            <div className="flex items-center gap-3 mb-10">
                <div className="w-10 h-10 bg-gradient-to-br from-memora-blue to-purple-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-200">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
                        <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 6.433 11.42 11.236 12.041a.75.75 0 00.528 0c4.803-.621 11.236-6.049 11.236-12.041 0-1.472-.34-2.883-.945-4.148a.75.75 0 00-.722-.515 11.209 11.209 0 01-7.877-3.08zM12 19.34c-2.313-.4-6-3.237-6-8.59 0-.84.092-1.648.261-2.421 2.316.516 4.795.556 7.151.13.78 1.602 1.305 3.323 1.54 5.093.076.57.14 1.139.191 1.696A13.754 13.754 0 0112 19.34z" clipRule="evenodd" />
                    </svg>
                </div>
                <div>
                    <h1 className="font-sans font-bold text-xl text-slate-800 tracking-tight">Memora</h1>
                    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Enterprise Shield</p>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 flex flex-col gap-6">
                {/* Active Item */}
                <div className="flex items-center gap-3 px-4 py-4 bg-memora-blue text-white rounded-xl shadow-lg shadow-indigo-200 cursor-pointer font-medium relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white/10 opacity-0 hover:opacity-100 transition-opacity"></div>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Session History
                    <div className="ml-auto w-1.5 h-1.5 bg-white rounded-full"></div>
                </div>

                {/* Chat History List (Sub-navigation) */}
                <div className="pl-4 space-y-1 overflow-y-auto max-h-[300px] fancy-scrollbar">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 pl-2">Recent Chats</div>

                    <div
                        onClick={onNewChat}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-memora-blue font-medium hover:bg-indigo-50 rounded-lg cursor-pointer transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                        New Chat
                    </div>

                    {chatHistory.map((chat) => (
                        <div
                            key={chat.id}
                            onClick={() => onLoadChat(chat)}
                            className={`px-3 py-2 rounded-lg cursor-pointer text-sm truncate transition-all duration-200 border-l-2 ${currentChatId === chat.id
                                ? 'bg-indigo-50 text-indigo-700 border-memora-blue font-medium'
                                : 'text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-50'
                                }`}
                        >
                            {chat.title || 'New Chat'}
                        </div>
                    ))}
                </div>
            </nav>

            {/* Storage / Footer */}
            <div className="mt-auto pt-6">
                <div className="bg-memora-bg rounded-xl p-4 border border-indigo-50">
                    <div className="flexjustify-between items-center mb-2">
                        <span className="text-xs font-semibold text-slate-500">Storage Capacity</span>
                        <span className="text-xs font-bold text-memora-blue float-right">78%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-memora-blue h-1.5 rounded-full w-[78%]"></div>
                    </div>
                    <div className="mt-2 text-[10px] text-slate-400">1.2GB of 1.5GB allocated</div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
