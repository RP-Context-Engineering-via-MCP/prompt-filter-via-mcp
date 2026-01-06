const Message = ({ role, content }) => {
    const isUser = role === 'user';

    return (
        <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
            <div className={`max-w-[80%] md:max-w-[70%] px-4 py-3 rounded-2xl text-base leading-relaxed ${isUser
                ? 'bg-stone-200 text-stone-900 rounded-tr-sm'
                : 'bg-white border border-stone-200 text-stone-800 shadow-sm rounded-tl-sm'
                }`}>
                <div className="whitespace-pre-wrap">{content}</div>
            </div>
        </div>
    );
};

export default Message;
