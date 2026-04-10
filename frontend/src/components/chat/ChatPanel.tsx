"use client";

import { useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { sendChatMessage, type ChatMessage } from "@/lib/api";

export default function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    const updatedHistory = [...messages, userMsg];
    setMessages(updatedHistory);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage(text, messages);
      setMessages([
        ...updatedHistory,
        { role: "assistant", content: res.response },
      ]);
    } catch {
      setMessages([
        ...updatedHistory,
        {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-[60] flex h-12 w-12 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg transition-transform hover:scale-105 active:scale-95"
        aria-label={open ? "Close chat" : "Open chat"}
      >
        {open ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-20 right-6 z-[60] flex h-[28rem] w-96 flex-col overflow-hidden border border-neutral-200 bg-white shadow-xl">
          {/* Header */}
          <div className="border-b border-neutral-200 px-4 py-3">
            <span
              className="text-[10px] font-medium uppercase tracking-[0.2em] text-neutral-500"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Sales Intelligence Agent
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && !loading && (
              <p className="pt-8 text-center text-sm font-light text-neutral-400">
                Ask me anything about your leads&hellip;
                <br />
                <span className="mt-2 block text-xs text-neutral-300">
                  &ldquo;Who are the top Master Elite contractors?&rdquo;
                </span>
              </p>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={
                  msg.role === "user"
                    ? "ml-10 bg-neutral-900 px-3 py-2 text-white"
                    : "mr-4 border border-neutral-100 bg-neutral-50 px-3 py-2"
                }
              >
                {msg.role === "user" ? (
                  <p className="whitespace-pre-wrap text-sm font-light leading-relaxed">
                    {msg.content}
                  </p>
                ) : (
                  <div className="prose-chat text-sm font-light leading-relaxed">
                    <ReactMarkdown
                      components={{
                        h3: ({ children }) => (
                          <h3 className="mt-3 mb-1 text-sm font-semibold">{children}</h3>
                        ),
                        h4: ({ children }) => (
                          <h4 className="mt-2 mb-1 text-sm font-medium">{children}</h4>
                        ),
                        p: ({ children }) => (
                          <p className="mb-1.5 last:mb-0">{children}</p>
                        ),
                        ul: ({ children }) => (
                          <ul className="mb-1.5 ml-4 list-disc space-y-0.5">{children}</ul>
                        ),
                        ol: ({ children }) => (
                          <ol className="mb-1.5 ml-4 list-decimal space-y-0.5">{children}</ol>
                        ),
                        li: ({ children }) => (
                          <li className="text-sm">{children}</li>
                        ),
                        strong: ({ children }) => (
                          <strong className="font-semibold">{children}</strong>
                        ),
                        a: ({ href, children }) => (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline underline-offset-2"
                          >
                            {children}
                          </a>
                        ),
                        hr: () => <hr className="my-2 border-neutral-200" />,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="mr-4 border border-neutral-100 bg-neutral-50 px-3 py-2">
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400" />
                  <span
                    className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400"
                    style={{ animationDelay: "0.2s" }}
                  />
                  <span
                    className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400"
                    style={{ animationDelay: "0.4s" }}
                  />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2 border-t border-neutral-200 px-4 py-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your leads..."
              disabled={loading}
              className="flex-1 border border-neutral-200 bg-white px-3 py-2 text-sm font-light text-neutral-900 placeholder:text-neutral-400 focus:border-neutral-900 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-neutral-900 px-3 py-2 text-xs font-medium tracking-wide text-white transition-opacity hover:opacity-90 disabled:opacity-40"
              style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
