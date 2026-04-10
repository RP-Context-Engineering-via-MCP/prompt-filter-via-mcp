import React, { useState, useEffect } from 'react';

const MCPAccessTokenModal = ({ isOpen, onClose }) => {
    const [token, setToken] = useState('');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        if (isOpen) {
            const savedToken = localStorage.getItem('mcp_token');
            if (savedToken) {
                setToken(savedToken);
            }
        }
    }, [isOpen]);

    const handleGenerate = () => {
        // Generate a random secure-looking token
        const array = new Uint8Array(24);
        window.crypto.getRandomValues(array);
        const newToken = 'mcp_' + Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
        
        setToken(newToken);
        localStorage.setItem('mcp_token', newToken);
    };

    const handleCopy = () => {
        if (token) {
            navigator.clipboard.writeText(token).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            });
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm" onClick={onClose}>
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-fade-in"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="bg-gradient-to-br from-emerald-600 to-emerald-800 px-6 py-5 relative overflow-hidden">
                    <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full border border-white/10" />
                    <div className="absolute -bottom-4 -left-4 w-24 h-24 rounded-full border border-white/10" />
                    <div className="relative flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-white">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-white">MCP Access Token</h3>
                                <p className="text-xs text-emerald-100">Manage your connection token</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div className="px-6 py-6 border-b border-slate-100">
                    <p className="text-sm text-slate-600 mb-6">
                        This token gives external clients full access to your personalized AI context through the Model Context Protocol. Keep it secure and do not share it.
                    </p>

                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Your Private Token</label>
                        {token ? (
                            <div className="flex items-stretch gap-2">
                                <div className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl overflow-x-auto font-mono text-sm text-slate-800 whitespace-nowrap scrollbar-none">
                                    {token}
                                </div>
                                <button
                                    onClick={handleCopy}
                                    className={`flex-shrink-0 px-4 rounded-xl text-sm font-bold border transition-all duration-200 flex items-center gap-1.5 ${
                                        copied
                                            ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                                            : 'bg-white border-slate-200 text-slate-500 hover:border-emerald-300 hover:text-emerald-600 hover:bg-emerald-50'
                                    }`}
                                >
                                    {copied ? 'Copied!' : 'Copy'}
                                </button>
                            </div>
                        ) : (
                            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-500 text-center italic">
                                No token generated yet.
                            </div>
                        )}
                    </div>
                </div>

                <div className="px-6 py-5 bg-slate-50 flex items-center justify-between">
                    <button
                        onClick={handleGenerate}
                        className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-[0_2px_10px_-3px_rgba(5,150,105,0.4)] transition-all flex items-center gap-2"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                        </svg>
                        {token ? 'Regenerate Token' : 'Generate Token'}
                    </button>
                    <button
                        onClick={onClose}
                        className="px-4 py-2.5 text-sm font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-200 rounded-xl transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MCPAccessTokenModal;
