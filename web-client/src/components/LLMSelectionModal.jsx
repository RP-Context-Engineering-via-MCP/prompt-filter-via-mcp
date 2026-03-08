import React, { useState } from 'react';

const models = [
    {
        id: 'chatgpt',
        name: 'ChatGPT',
        label: 'GPT-4o',
        description: "OpenAI's most capable model for reasoning and creativity",
        selectedBg: 'bg-emerald-50',
        selectedBorder: 'border-emerald-400',
        selectedText: 'text-emerald-700',
        hoverBorder: 'hover:border-emerald-200',
        iconBg: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
        dotColor: 'bg-emerald-500',
        badgeBg: 'bg-emerald-100 text-emerald-700',
        abbr: 'GPT',
    },
    {
        id: 'claude',
        name: 'Claude',
        label: 'Claude 3.5',
        description: "Anthropic's model with advanced analysis and safety",
        selectedBg: 'bg-orange-50',
        selectedBorder: 'border-orange-400',
        selectedText: 'text-orange-700',
        hoverBorder: 'hover:border-orange-200',
        iconBg: 'bg-gradient-to-br from-orange-500 to-orange-600',
        dotColor: 'bg-orange-400',
        badgeBg: 'bg-orange-100 text-orange-700',
        abbr: 'AI',
    },
];

const LLMSelectionModal = ({ isOpen, onClose, onConfirm }) => {
    const [selectedModel, setSelectedModel] = useState(null);

    if (!isOpen) return null;

    const handleConfirm = () => {
        if (selectedModel) onConfirm(selectedModel);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-fade-in">

                {/* Gradient Header */}
                <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 px-6 py-7 text-center relative overflow-hidden">
                    {/* Subtle ring decoration */}
                    <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full border border-white/10"></div>
                    <div className="absolute -bottom-4 -left-4 w-24 h-24 rounded-full border border-white/10"></div>

                    <div className="relative">
                        <div className="w-12 h-12 bg-white/15 rounded-2xl flex items-center justify-center mx-auto mb-3">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-white">
                                <path fillRule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.5 9.75c0 5.992 4.434 11.42 9.236 12.041a.75.75 0 00.528 0C17.066 21.17 21.5 15.742 21.5 9.75a12.74 12.74 0 00-.385-3.13.75.75 0 00-.722-.514 11.209 11.209 0 01-7.877-3.08z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <h3 className="text-lg font-bold text-white">Start a New Conversation</h3>
                        <p className="text-sm text-indigo-200 mt-1">Choose your AI model to begin</p>
                    </div>
                </div>

                {/* Model Cards */}
                <div className="p-5 grid grid-cols-2 gap-3">
                    {models.map((model) => {
                        const isSelected = selectedModel === model.id;
                        return (
                            <button
                                key={model.id}
                                onClick={() => setSelectedModel(model.id)}
                                className={`relative flex flex-col items-start p-4 border-2 rounded-2xl text-left transition-all duration-200 group ${
                                    isSelected
                                        ? `${model.selectedBg} ${model.selectedBorder} shadow-sm`
                                        : `bg-slate-50 border-slate-200 ${model.hoverBorder} hover:bg-white hover:shadow-sm`
                                }`}
                            >
                                {/* Selected checkmark */}
                                {isSelected && (
                                    <div className="absolute top-3 right-3 w-4 h-4 rounded-full bg-white flex items-center justify-center shadow-sm">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={`w-3 h-3 ${model.selectedText}`}>
                                            <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                )}

                                {/* Model Icon */}
                                <div className={`w-10 h-10 rounded-xl ${model.iconBg} flex items-center justify-center mb-3 shadow-sm`}>
                                    <span className="text-white text-xs font-bold">{model.abbr}</span>
                                </div>

                                {/* Model Info */}
                                <div className="font-bold text-slate-800 text-sm">{model.name}</div>
                                <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded mt-1 mb-1.5 ${model.badgeBg}`}>{model.label}</div>
                                <p className="text-[11px] text-slate-500 leading-snug">{model.description}</p>

                                {/* Live indicator */}
                                <div className="flex items-center gap-1 mt-3">
                                    <div className={`w-1.5 h-1.5 rounded-full ${model.dotColor}`}></div>
                                    <span className="text-[10px] font-semibold text-slate-400">Available</span>
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Footer Buttons */}
                <div className="px-5 pb-5 flex flex-col gap-2">
                    <button
                        onClick={handleConfirm}
                        disabled={!selectedModel}
                        className={`w-full py-3 rounded-xl text-sm font-bold transition-all duration-200 ${
                            selectedModel
                                ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-indigo-sm hover:shadow-indigo-md hover:from-indigo-500 hover:to-indigo-600'
                                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        }`}
                    >
                        Start Conversation
                        {selectedModel && (
                            <span className="ml-2 opacity-80">→</span>
                        )}
                    </button>
                    <button
                        onClick={onClose}
                        className="w-full py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LLMSelectionModal;
