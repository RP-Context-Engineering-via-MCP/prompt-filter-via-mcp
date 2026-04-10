import React, { useState } from 'react';

const MCP_BASE_URL = import.meta.env.VITE_MCP_PUBLIC_URL || 'https://your-ngrok-url.ngrok.io';

const TABS = [
    { id: 'chatgpt', label: 'ChatGPT', abbr: 'GPT', iconBg: 'bg-gradient-to-br from-emerald-500 to-emerald-600', activeTab: 'border-emerald-400 text-emerald-700 bg-emerald-50', dot: 'bg-emerald-500' },
    { id: 'claudeai', label: 'Claude.ai', abbr: 'AI', iconBg: 'bg-gradient-to-br from-orange-500 to-orange-600', activeTab: 'border-orange-400 text-orange-700 bg-orange-50', dot: 'bg-orange-400' },
    { id: 'claudedesktop', label: 'Claude Desktop', abbr: 'CD', iconBg: 'bg-gradient-to-br from-slate-600 to-slate-800', activeTab: 'border-slate-500 text-slate-700 bg-slate-50', dot: 'bg-slate-500' },
];

const CopyField = ({ label, value, mono = true }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(value).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="mb-3">
            {label && <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">{label}</p>}
            <div className="flex items-stretch gap-2">
                <div className={`flex-1 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl overflow-x-auto ${mono ? 'font-mono' : ''} text-xs text-slate-700 whitespace-nowrap scrollbar-none`}>
                    {value}
                </div>
                <button
                    onClick={handleCopy}
                    className={`flex-shrink-0 px-3 rounded-xl text-xs font-bold border transition-all duration-200 flex items-center gap-1.5 ${
                        copied
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                            : 'bg-white border-slate-200 text-slate-500 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50'
                    }`}
                >
                    {copied ? (
                        <>
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                                <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                            </svg>
                            Copied
                        </>
                    ) : (
                        <>
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                            </svg>
                            Copy
                        </>
                    )}
                </button>
            </div>
        </div>
    );
};

const Step = ({ num, text }) => (
    <div className="flex items-start gap-2.5 text-xs text-slate-500">
        <div className="flex-shrink-0 w-4 h-4 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-[9px] font-bold mt-0.5">
            {num}
        </div>
        <span className="leading-relaxed">{text}</span>
    </div>
);

const ChatGPTTab = ({ token }) => (
    <div className="space-y-4">
        <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-xs text-emerald-700 font-medium">
            ChatGPT connects via <span className="font-bold">Streamable HTTP</span> transport at the <code className="bg-emerald-100 px-1 rounded">/mcp</code> endpoint.
        </div>
        <CopyField label="MCP Server URL" value={`${MCP_BASE_URL}/mcp`} />
        <CopyField label="Auth Header" value={`Authorization: Bearer ${token}`} />
        <div className="space-y-2 pt-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Setup Steps</p>
            <Step num="1" text="Go to ChatGPT → Settings → Beta Features → Model Context Protocol" />
            <Step num="2" text='Click "Add MCP Server" and paste the Server URL above' />
            <Step num="3" text="Under Authentication, select Bearer Token and paste the Auth Header value" />
            <Step num="4" text="Save and start a new conversation — Memora context will be injected automatically" />
        </div>
    </div>
);

const ClaudeAITab = ({ token }) => (
    <div className="space-y-4">
        <div className="p-3 bg-orange-50 border border-orange-100 rounded-xl text-xs text-orange-700 font-medium">
            Claude.ai connects via <span className="font-bold">SSE</span> transport. Add the server URL and auth header in your integration settings.
        </div>
        <CopyField label="MCP Server URL" value={`${MCP_BASE_URL}/sse`} />
        <CopyField label="Auth Header" value={`Authorization: Bearer ${token}`} />
        <div className="space-y-2 pt-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Setup Steps</p>
            <Step num="1" text="Go to Claude.ai → Settings → Integrations → MCP Servers" />
            <Step num="2" text='Click "Add Server" and paste the MCP Server URL above' />
            <Step num="3" text="Add a custom header: Authorization with the Bearer token value" />
            <Step num="4" text="Enable the integration — Memora will enrich every message with your context" />
        </div>
    </div>
);

const DESKTOP_CONFIG = (token) =>
    JSON.stringify(
        {
            mcpServers: {
                memora: {
                    url: `${MCP_BASE_URL}/sse`,
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                },
            },
        },
        null,
        2
    );

const ClaudeDesktopTab = ({ token }) => {
    const config = DESKTOP_CONFIG(token);
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(config).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="space-y-4">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 font-medium">
                Paste this into your <code className="bg-slate-100 px-1 rounded">claude_desktop_config.json</code> file under <code className="bg-slate-100 px-1 rounded">mcpServers</code>.
            </div>

            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Config Block</p>
                    <button
                        onClick={handleCopy}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold border transition-all duration-200 ${
                            copied
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                                : 'bg-white border-slate-200 text-slate-500 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50'
                        }`}
                    >
                        {copied ? (
                            <>
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                                </svg>
                                Copied!
                            </>
                        ) : (
                            <>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                                </svg>
                                Copy All
                            </>
                        )}
                    </button>
                </div>
                <pre className="bg-slate-900 text-emerald-300 text-[11px] font-mono p-4 rounded-xl overflow-x-auto leading-relaxed border border-slate-700 max-h-44">
                    {config}
                </pre>
            </div>

            <div className="space-y-2 pt-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Setup Steps</p>
                <Step num="1" text='Open Claude Desktop → Settings → Developer → "Edit Config"' />
                <Step num="2" text="Paste the config block above (merge with existing mcpServers if present)" />
                <Step num="3" text="Save the file and restart Claude Desktop" />
                <Step num="4" text='Look for "memora" in the MCP tools panel — Memora context is now active' />
            </div>
        </div>
    );
};

const TAB_CONTENT = (token) => ({
    chatgpt: <ChatGPTTab token={token} />,
    claudeai: <ClaudeAITab token={token} />,
    claudedesktop: <ClaudeDesktopTab token={token} />,
});

const MCPConnectModal = ({ isOpen, onClose }) => {
    const [activeTab, setActiveTab] = useState('chatgpt');
    const token = localStorage.getItem('mcp_token') || 'your-mcp-token';
    const isTokenMissing = !localStorage.getItem('mcp_token');

    if (!isOpen) return null;

    const activeTabConfig = TABS.find((t) => t.id === activeTab);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm" onClick={onClose}>
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-fade-in"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 px-6 py-5 relative overflow-hidden">
                    <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full border border-white/10" />
                    <div className="absolute -bottom-4 -left-4 w-24 h-24 rounded-full border border-white/10" />
                    <div className="relative flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-white">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="text-base font-bold text-white">Connect to Memora</h3>
                                <p className="text-xs text-indigo-200">Add your MCP server to an external LLM client</p>
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

                {/* Token notice */}
                {isTokenMissing && (
                    <div className="px-6 pt-4">
                        <div className="flex items-center gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 text-amber-500 flex-shrink-0">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                            </svg>
                            <p className="text-xs text-amber-700">
                                <span className="font-bold">MCP Token required.</span> Generate yours by clicking your{' '}
                                <span className="font-semibold text-amber-900 border-b border-amber-900 border-dotted pb-0.5">Profile (AR)</span> icon in the top right.
                            </p>
                        </div>
                    </div>
                )}

                {/* Tabs */}
                <div className="px-6 pt-4 flex gap-2">
                    {TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold border transition-all duration-200 ${
                                activeTab === tab.id
                                    ? tab.activeTab + ' border-current shadow-sm'
                                    : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
                            }`}
                        >
                            <div className={`w-4 h-4 rounded-md ${tab.iconBg} flex items-center justify-center`}>
                                <span className="text-white text-[8px] font-bold leading-none">{tab.abbr}</span>
                            </div>
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="px-6 py-4 max-h-[380px] overflow-y-auto">
                    {TAB_CONTENT(token)[activeTab]}
                </div>

                {/* Footer */}
                <div className="px-6 pb-5">
                    <div className="h-px bg-slate-100 mb-4" />
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                            <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${activeTabConfig.dot}`} />
                            <span className="text-[11px] text-slate-400 font-medium">MCP Server: <span className="text-slate-600 font-semibold">{MCP_BASE_URL}</span></span>
                        </div>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MCPConnectModal;
