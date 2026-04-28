import { useEffect, useRef, useState } from 'react';
import { Loader, MessageCircle, Send, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';

import api from '../services/api';
import '../styles/chatbot.css';

export default function ChatBot({ onClose }) {
  const [messages, setMessages] = useState([
    {
      id: 'intro',
      type: 'assistant',
      content: 'Hi! I\'m your InventAI Assistant. I can help you understand what you can do with your sales data. Ask me anything like:\n\n- "What features are available?"\n- "How do I get demand forecasts?"\n- "What are reorder recommendations?"\n- "How can I track market prices?"\n- "What alerts can I set up?"',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.streamChat({ message: input });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let assistantMessage = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const json = JSON.parse(data);
              fullContent += json.content || '';

              if (!assistantMessage) {
                assistantMessage = {
                  id: Date.now() + 1,
                  type: 'assistant',
                  content: fullContent,
                };
                setMessages((prev) => [...prev, assistantMessage]);
              } else {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessage.id
                      ? { ...msg, content: fullContent }
                      : msg
                  )
                );
              }
            } catch {
              // Ignore JSON parse errors
            }
          }
        }
      }
    } catch (error) {
      toast.error(error.message || 'Failed to send message');
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          type: 'error',
          content: 'Sorry, I encountered an error. Please try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <MessageCircle size={20} />
          <h3>InventAI Assistant</h3>
        </div>
        <button className="chatbot-close" onClick={onClose} aria-label="Close chat">
          <X size={16} />
        </button>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`chatbot-message ${message.type === 'user' ? 'user-message' : message.type === 'error' ? 'error-message' : 'assistant-message'}`}
          >
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="chatbot-message assistant-message">
            <div className="message-content">
              <Loader size={16} className="spinner" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input-area">
        <div className="chatbot-input-wrapper">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about features, forecasts, reorders..."
            disabled={loading}
            rows="2"
            className="chatbot-input"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="chatbot-send-btn"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
