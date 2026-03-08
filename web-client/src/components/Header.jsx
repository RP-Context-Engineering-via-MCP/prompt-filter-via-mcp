import React, { useState, useRef, useEffect } from 'react';

const Header = ({ selectedModel, sessionContext, onSessionContextChange }) => {
    const [isContextOpen, setIsContextOpen] = useState(false);
    const [contexts, setContexts] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const dropdownRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsContextOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
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

    const getModelConfig = () => {
        if (selectedModel === 'claude') return { label: 'Claude', dotColor: 'bg-orange-400', badgeClass: 'bg-orange-50 text-orange-700 border-orange-200' };
        if (selectedModel === 'chatgpt') return { label: 'ChatGPT', dotColor: 'bg-emerald-400', badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
        return { label: 'No model', dotColor: 'bg-slate-300', badgeClass: 'bg-slate-50 text-slate-500 border-slate-200' };
    };

    const modelConfig = getModelConfig();

    return (
        <header className="flex items-center justify-between px-6 py-4 bg-memora-bg border-b border-slate-100 z-10 flex-shrink-0">
            {/* Left: Model Badge */}
            <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest hidden sm:block">Model</span>
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold border ${modelConfig.badgeClass}`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${modelConfig.dotColor} ${selectedModel ? 'animate-pulse' : ''}`}></div>
                    {modelConfig.label}
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-3">

                {/* Session Context Dropdown */}
                <div className="relative" ref={dropdownRef}>
                    <button
                        onClick={() => setIsContextOpen(!isContextOpen)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all duration-200 ${sessionContext
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md hover:bg-indigo-700'
                            : 'bg-white text-slate-700 border-slate-200 shadow-sm hover:border-indigo-300'
                            }`}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
                        </svg>
                        <span>{sessionContext ? sessionContext.title : 'Session Context'}</span>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className={`w-3 h-3 transition-transform duration-200 ${isContextOpen ? 'rotate-180' : ''}`}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                        </svg>
                    </button>

                    {isContextOpen && (
                        <div className="absolute top-full right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden z-50 animate-fade-in">
                            <div className="p-2">
                                <div className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    Active Context
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
                                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${ctx.tagColor}`}>
                                                    {ctx.tag}
                                                </span>
                                            </div>
                                        </div>
                                        {sessionContext?.id === ctx.id && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0"></div>
                                        )}
                                    </button>
                                ))}

                                <div className="h-px bg-slate-100 my-1.5"></div>

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
                                    <div className="w-8 h-8 rounded-lg border-2 border-dashed border-slate-300 flex items-center justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </div>
                                    <span className="text-sm font-medium">No Context</span>
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Divider */}
                <div className="h-6 w-px bg-slate-200"></div>

                {/* User Profile */}
                <div className="flex items-center gap-2.5">
                    <div className="text-right hidden sm:block">
                        <div className="text-xs font-bold text-slate-800 leading-tight">Alex Rivera</div>
                        <div className="text-[9px] font-bold text-emerald-500 uppercase tracking-widest">Security Lead</div>
                    </div>
                    <div className="relative cursor-pointer">
                        <div className="w-9 h-9 bg-gradient-to-br from-slate-700 to-slate-900 rounded-xl flex items-center justify-center text-white text-xs font-bold shadow-sm hover:shadow-md transition-shadow">
                            AR
                        </div>
                        <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 border-2 border-white rounded-full"></div>
                    </div>
                </div>

                {/* Settings Button */}
                <button className="w-9 h-9 flex items-center justify-center bg-slate-800 text-white rounded-xl hover:bg-slate-700 shadow-sm hover:shadow-md transition-all duration-200">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>
            </div>
        </header>
    );
};

export default Header;
