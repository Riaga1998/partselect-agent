import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";
import ProductCard from "./ProductCard";
import SupportCard from "./SupportCard";
import Chip from "./Chip";

// Chips shown under the greeting (no agent turn yet to generate them).
const STARTER_CHIPS = [
  "My ice maker stopped working",
  "Find a dishwasher part",
  "Track my order",
];

/**
 * Turn one assistant message's tool_calls into structured card components.
 * The agent already returns full Part / CompatibilityResult / support data.
 *
 * Parts are de-duplicated by ps_number across all tool calls so the same part
 * doesn't render twice (e.g. when the agent calls both check_compatibility and
 * get_part_details). A part that carries a compatibility banner wins.
 */
function renderToolCards(toolCalls, addToCart) {
  if (!toolCalls || toolCalls.length === 0) return null;

  const partCards = new Map(); // ps_number -> { part, banner }
  const supportCards = [];

  const addPart = (part, banner) => {
    if (!part || !part.ps_number) return;
    const existing = partCards.get(part.ps_number);
    // Keep a banner if either the existing or the new entry has one.
    partCards.set(part.ps_number, {
      part,
      banner: banner || existing?.banner || null,
    });
  };

  toolCalls.forEach((call, i) => {
    const { tool, result } = call;
    if (!result) return;

    if (tool === "troubleshoot" && Array.isArray(result.candidate_parts)) {
      result.candidate_parts.forEach((p) => addPart(p));
    } else if (tool === "search_parts" && Array.isArray(result.parts)) {
      result.parts.forEach((p) => addPart(p));
    } else if (tool === "get_part_details" && result.ps_number && !result.error) {
      addPart(result);
    } else if (tool === "check_compatibility" && result.part) {
      addPart(result.part, { compatible: result.compatible, text: result.reason });
    } else if (tool === "escalate_to_support" && result.escalated) {
      supportCards.push(<SupportCard key={`support-${i}`} data={result} />);
    }
  });

  const cards = [
    ...[...partCards.values()].map(({ part, banner }) => (
      <ProductCard
        key={part.ps_number}
        part={part}
        banner={banner}
        addToCart={addToCart}
      />
    )),
    ...supportCards,
  ];

  return cards.length ? <div className="tool-cards">{cards}</div> : null;
}

function ChatWindow({ addToCart }) {
  const defaultMessage = [{
    role: "assistant",
    content: "Hi! I'm the PartSelect parts assistant. I can help you find refrigerator and dishwasher parts, check compatibility, walk through installations, and troubleshoot repairs. What do you need?",
    tool_calls: [],
    suggestions: STARTER_CHIPS,
  }];

  const [messages, setMessages] = useState(defaultMessage);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setShowScrollButton(!nearBottom);
  };

  const handleSend = async (inputText) => {
    const text = typeof inputText === "string" ? inputText : input;
    if (!text.trim() || loading) return;

    const userMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // Pass full history so the agent has multi-turn context
    const newMessage = await getAIMessage(text, messages);
    setMessages(prev => [...prev, newMessage]);
    setLoading(false);
  };

  const lastIndex = messages.length - 1;

  return (
    <div className="messages-container" ref={containerRef} onScroll={handleScroll}>
      {messages.map((message, index) => (
        <div key={index} className={`${message.role}-message-container`}>
          {message.content && (
            <div className={`message ${message.role}-message`}>
              <div dangerouslySetInnerHTML={{
                __html: marked(message.content)
              }} />
            </div>
          )}

          {message.role === "assistant" && renderToolCards(message.tool_calls, addToCart)}

          {/* Suggestion chips: only under the latest assistant message, when idle */}
          {message.role === "assistant" &&
            index === lastIndex &&
            !loading &&
            message.suggestions &&
            message.suggestions.length > 0 && (
              <div className="chips-row">
                {message.suggestions.map((s, i) => (
                  <Chip key={i} label={s} onClick={handleSend} />
                ))}
              </div>
            )}
        </div>
      ))}

      {loading && (
        <div className="assistant-message-container">
          <div className="message assistant-message">
            <em>Looking that up...</em>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />

      {showScrollButton && (
        <button className="scroll-bottom-button" onClick={scrollToBottom} aria-label="Scroll to bottom">
          ↓
        </button>
      )}

      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a part, model, or repair..."
          disabled={loading}
          onKeyPress={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              handleSend(input);
              e.preventDefault();
            }
          }}
        />
        <button className="send-button" onClick={() => handleSend(input)} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;
