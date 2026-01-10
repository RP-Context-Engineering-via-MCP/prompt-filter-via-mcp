import React, { useState } from 'react';

const LLMSelectionModal = ({ isOpen, onClose, onConfirm }) => {
    const [selectedModel, setSelectedModel] = useState(null);

    if (!isOpen) return null;

    const handleConfirm = () => {
        if (selectedModel) {
            onConfirm(selectedModel);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all scale-100">

                {/* Header */}
                <div className="p-6 pb-2 text-center">
                    <h3 className="text-xl font-serif font-semibold text-gray-900">
                        Select LLM you want to talk to
                    </h3>
                </div>

                {/* Options */}
                <div className="p-6 grid grid-cols-2 gap-4">
                    {/* ChatGPT Option */}
                    <div
                        onClick={() => setSelectedModel('chatgpt')}
                        className={`cursor-pointer group flex flex-col items-center justify-center p-4 border-2 rounded-xl transition-all duration-200 ${selectedModel === 'chatgpt'
                                ? 'border-green-500 bg-green-50'
                                : 'border-gray-200 hover:border-green-200 hover:bg-gray-50'
                            }`}
                    >
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 text-white font-bold text-lg transition-colors ${selectedModel === 'chatgpt' ? 'bg-green-500' : 'bg-green-600'
                            }`}>
                            GPT
                        </div>
                        <span className={`font-medium ${selectedModel === 'chatgpt' ? 'text-green-700' : 'text-gray-600'}`}>
                            ChatGPT
                        </span>
                    </div>

                    {/* Claude Option */}
                    <div
                        onClick={() => setSelectedModel('claude')}
                        className={`cursor-pointer group flex flex-col items-center justify-center p-4 border-2 rounded-xl transition-all duration-200 ${selectedModel === 'claude'
                                ? 'border-orange-500 bg-orange-50'
                                : 'border-gray-200 hover:border-orange-200 hover:bg-gray-50'
                            }`}
                    >
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 text-white font-bold text-lg transition-colors ${selectedModel === 'claude' ? 'bg-orange-500' : 'bg-orange-600'
                            }`}>
                            Cl
                        </div>
                        <span className={`font-medium ${selectedModel === 'claude' ? 'text-orange-700' : 'text-gray-600'}`}>
                            Claude
                        </span>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 pt-2 flex flex-col gap-3">
                    <button
                        onClick={handleConfirm}
                        disabled={!selectedModel}
                        className={`w-full py-3 px-4 rounded-lg text-white font-medium transition-colors ${selectedModel
                                ? 'bg-primary hover:bg-primary-hover shadow-md'
                                : 'bg-gray-300 cursor-not-allowed'
                            }`}
                    >
                        Start Conversation
                    </button>
                    <button
                        onClick={onClose}
                        className="w-full py-2 px-4 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors text-sm font-medium"
                    >
                        Cancel
                    </button>
                </div>

            </div>
        </div>
    );
};

export default LLMSelectionModal;
