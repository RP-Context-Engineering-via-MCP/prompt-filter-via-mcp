import React, { useState, useRef, useEffect } from 'react';

const Header = ({ selectedModel, sessionContext, onSessionContextChange }) => {
    const [isContextOpen, setIsContextOpen] = useState(false);
    const [contexts, setContexts] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsContextOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    useEffect(() => {
        const fetchSessions = async () => {
            setIsLoading(true);
            setErrorMsg('');
            try {
                const userId = localStorage.getItem('userId') || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2';
                const response = await fetch(`http://localhost:8080/api/users/${userId}/sessions/`);

                if (!response.ok) throw new Error('Failed to fetch from user management service');

                const data = await response.json();

                // Map the backend session data to our UI format
                // data format: { total: 2, sessions: [{ session_id: '...', session_name: '...', created_at: '...' }] }
                if (data && data.sessions) {
                    const mappedContexts = data.sessions.map((s) => ({
                        id: s.session_id,
                        title: s.session_name || 'Untitled Session',
                        tag: 'MEMORA',
                        color: 'bg-indigo-100 text-indigo-700'
                    }));
                    setContexts(mappedContexts);
                } else {
                    setContexts([]);
                }
            } catch (error) {
                console.error('Session fetch error:', error);
                setErrorMsg('User Management API is offline. Cannot load sessions.');
            } finally {
                setIsLoading(false);
            }
        };

        if (isContextOpen && contexts.length === 0 && !errorMsg) {
            fetchSessions();
        }
    }, [isContextOpen, contexts.length, errorMsg]);

    const handleSessionSelect = async (ctx) => {
        const userId = localStorage.getItem('userId') || '5ca4d3ee-a139-44f9-9f9a-84655025a8f2';
        try {
            if (ctx) {
                // Update session on the backend user service
                await fetch(`http://localhost:8080/api/users/${userId}/sessions/${ctx.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        } catch (error) {
            console.error('Failed to update session on backend', error);
            // Optionally set error toast or message here
        }
        onSessionContextChange(ctx);
        setIsContextOpen(false);
    };

    return (
        <header className="flex items-center justify-between px-8 py-5 bg-transparent z-10">
            {/* Model Display */}
            <div className="flex-1 max-w-2xl">
                <div className="flex items-center gap-3">
                    <div className="text-sm font-medium text-slate-500">Current Model:</div>
                    <div className={`px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 ${selectedModel === 'claude'
                        ? 'bg-orange-50 text-orange-700 border border-orange-200'
                        : selectedModel === 'chatgpt'
                            ? 'bg-green-50 text-green-700 border border-green-200'
                            : 'bg-slate-50 text-slate-600 border border-slate-200'
                        }`}>
                        {selectedModel === 'claude' && (
                            <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                        )}
                        {selectedModel === 'chatgpt' && (
                            <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        )}
                        {!selectedModel && (
                            <div className="w-2 h-2 rounded-full bg-slate-400"></div>
                        )}
                        {selectedModel === 'claude' ? 'Claude' : selectedModel === 'chatgpt' ? 'ChatGPT' : 'No Model Selected'}
                    </div>
                </div>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-6 ml-6">

                {/* Session Context Dropdown */}
                <div className="relative" ref={dropdownRef}>
                    <button
                        onClick={() => setIsContextOpen(!isContextOpen)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all duration-200 ${sessionContext
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md hover:bg-indigo-700'
                            : 'bg-white text-slate-700 border-slate-200 shadow-sm hover:border-indigo-300'
                            }`}
                    >
                        <span className="text-sm font-medium">
                            {sessionContext ? sessionContext.title : 'Session Context'}
                        </span>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className={`w-4 h-4 transition-transform ${isContextOpen ? 'rotate-180' : ''}`}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                        </svg>
                    </button>

                    {/* Dropdown Menu */}
                    {isContextOpen && (
                        <div className="absolute top-full right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
                            <div className="p-2 space-y-1">
                                <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                    Select Active Context
                                </div>

                                {contexts.map((ctx) => (
                                    <button
                                        key={ctx.id}
                                        onClick={() => handleSessionSelect(ctx)}
                                        className={`w-full text-left px-3 py-3 rounded-xl flex items-center justify-between group transition-colors ${sessionContext?.id === ctx.id
                                            ? 'bg-indigo-50 border border-indigo-100'
                                            : 'hover:bg-slate-50 border border-transparent'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${sessionContext?.id === ctx.id ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-500 group-hover:bg-white group-hover:shadow-sm'
                                                }`}>
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                                            </div>
                                            <div>
                                                <div className={`text-sm font-semibold ${sessionContext?.id === ctx.id ? 'text-indigo-900' : 'text-slate-700'}`}>
                                                    {ctx.title}
                                                </div>
                                                <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded inline-block mt-0.5 ${ctx.color}`}>
                                                    {ctx.tag}
                                                </div>
                                            </div>
                                        </div>
                                        {sessionContext?.id === ctx.id && (
                                            <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                        )}
                                    </button>
                                ))}

                                <div className="h-px bg-slate-100 my-1"></div>

                                {isLoading ? (
                                    <div className="px-3 py-4 text-center text-sm font-medium text-slate-500">
                                        Loading sessions...
                                    </div>
                                ) : errorMsg ? (
                                    <div className="px-3 py-4 text-center text-sm font-medium text-red-500 bg-red-50 rounded-xl m-1 border border-red-100">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mx-auto mb-1 opacity-75" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        {errorMsg}
                                    </div>
                                ) : contexts.length === 0 ? (
                                    <div className="px-3 py-4 text-center text-sm font-medium text-slate-500">
                                        No active sessions found.
                                    </div>
                                ) : null}

                                <button
                                    onClick={() => handleSessionSelect(null)}
                                    className={`w-full text-left px-3 py-3 rounded-xl flex items-center gap-3 transition-colors ${!sessionContext
                                        ? 'bg-slate-50 text-slate-800'
                                        : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                                        }`}
                                >
                                    <div className="w-10 h-10 rounded-lg border-2 border-dashed border-slate-300 flex items-center justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                                    </div>
                                    <span className="text-sm font-medium">No Session Context</span>
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* User Profile */}
                <div className="flex items-center gap-3 pl-6 border-l border-slate-200/50">
                    <div className="text-right hidden sm:block">
                        <div className="text-sm font-bold text-slate-800">Alex Rivera</div>
                        <div className="text-[10px] font-bold text-green-500 uppercase tracking-wide">Security Lead</div>
                    </div>
                    <div className="relative cursor-pointer group">
                        <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center text-white font-bold shadow-md group-hover:shadow-lg transition-all duration-200">
                            AR
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full"></div>
                    </div>
                </div>

                <button className="p-2.5 bg-white text-slate-500 hover:text-memora-blue hover:bg-white rounded-xl shadow-sm border border-transparent hover:border-indigo-50 transition-all duration-200">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                    </svg>
                    <span className="absolute top-6 right-16 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white"></span>
                </button>

                <button className="p-2.5 bg-slate-800 text-white rounded-xl shadow-md hover:shadow-lg hover:bg-slate-700 transition-all duration-200">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
                    </svg>
                </button>
            </div>
        </header>
    );
};

export default Header;
