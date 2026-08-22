/** Analyst's Ledger visual contract: conversational intelligence is organized like a compact research memo. */

import { ArrowUp, Bot, LoaderCircle, MessageSquareText, SendHorizontal, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";

export type ChatMessage = { id: string; role: "user" | "agent"; content: string; pending?: boolean };

const prompts = ["What is the key risk?", "Summarize the news flow", "Pressure-test the thesis"];

export function ChatPanel({
  messages,
  isLoading,
  disabled,
  onSend,
}: {
  messages: ChatMessage[];
  isLoading: boolean;
  disabled?: boolean;
  onSend: (message: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, isLoading]);

  function submit(message = draft) {
    const value = message.trim();
    if (!value || isLoading || disabled) return;
    setDraft("");
    onSend(value);
  }

  return (
    <section className="ledger-panel flex min-h-[580px] flex-col overflow-hidden" aria-label="Financial AI chat">
      <div className="relative flex items-center justify-between border-b border-[#e2dbd0] px-5 py-4">
        <span className="absolute bottom-0 left-5 h-0.5 w-10 bg-[#0e8f83]" />
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-full bg-[#1d2928] text-[#f8f4ed]">
            <MessageSquareText className="size-3.5" />
          </span>
          <div>
            <p className="ledger-label">Conversational intelligence</p>
            <h2 className="mt-0.5 font-serif text-lg tracking-[-0.03em] text-[#1e2928]">Ask the agent</h2>
          </div>
        </div>
        <span className={cn("border px-1.5 py-1 text-[9px] font-bold uppercase tracking-[0.12em]", disabled ? "border-[#e8c8c1] text-[#a05245]" : "border-[#c9ded9] text-[#0e8f83]")}>{disabled ? "Desk offline" : "Live lane"}</span>
      </div>

      <div className="flex items-center justify-between border-b border-[#eee7dc] bg-[#faf7f1] px-5 py-2 text-[9px] font-bold uppercase tracking-[0.12em] text-[#7e8580]"><span>Session ledger</span><span>{messages.length ? `${Math.ceil(messages.length / 2)} research turn${messages.length > 2 ? "s" : ""}` : "No active brief"}</span></div>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="rounded-sm border border-[#e2dbd0] bg-[#fcfaf6] p-4">
            <div className="flex items-center gap-2 text-[#2b3533]">
              <Bot className="size-4 text-[#0e8f83]" />
            <p className="text-sm font-medium">Research with the Groq finance agent.</p>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-[#747c78]">Open an evidence trail: ask for a company brief, a risk review, or a tool-sourced market update.</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={cn("flex gap-2.5", message.role === "user" && "justify-end")}>
              {message.role === "agent" && <Bot className="mt-1 size-4 shrink-0 text-[#0e8f83]" />}
              <div
                className={cn(
                  "max-w-[90%] text-sm leading-relaxed",
                  message.role === "user" ? "rounded-sm bg-[#1e2928] px-3.5 py-2.5 text-[#f8f4ed]" : "agent-markdown text-[#3b4542]",
                )}
              >
                {message.pending ? <LoaderCircle className="size-4 animate-spin text-[#0e8f83]" /> : message.role === "agent" ? <Streamdown>{message.content}</Streamdown> : message.content}
              </div>
              {message.role === "user" && <UserRound className="mt-1 size-4 shrink-0 text-[#68716d]" />}
            </div>
          ))
        )}
      </div>

      <div className="border-t border-[#e2dbd0] bg-[#f8f5ef] p-4">
        <div className="mb-3"><p className="ledger-label mb-2">Research prompts</p><div className="flex gap-2 overflow-x-auto pb-1">
          {prompts.map((prompt) => (
            <button key={prompt} type="button" onClick={() => submit(prompt)} disabled={disabled || isLoading} className="whitespace-nowrap border-b border-[#cfc8bc] pb-1 text-[11px] font-semibold text-[#58615e] transition-colors hover:border-[#0e8f83] hover:text-[#0e8f83] disabled:opacity-40">
              {prompt}
            </button>
          ))}</div></div>
        <div className="flex items-end gap-2 rounded-sm border border-[#cfc8bc] bg-[#fffdf9] p-1.5 focus-within:border-[#0e8f83] focus-within:ring-2 focus-within:ring-[#0e8f83]/10">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={disabled ? "Connect AgentOS to open the research lane" : "Enter a research instruction…"}
            disabled={disabled || isLoading}
            rows={2}
            className="min-h-[42px] flex-1 resize-none bg-transparent px-2 py-1 text-sm text-[#263130] outline-none placeholder:text-[#929894] disabled:cursor-not-allowed"
          />
          <button type="button" onClick={() => submit()} disabled={!draft.trim() || disabled || isLoading} className="grid size-9 shrink-0 place-items-center rounded-sm bg-[#0e8f83] text-white transition-all duration-150 hover:bg-[#08766d] active:scale-[0.97] disabled:cursor-not-allowed disabled:bg-[#b4c1bc]" aria-label="Send message">
            {isLoading ? <LoaderCircle className="size-4 animate-spin" /> : <SendHorizontal className="size-4" />}
          </button>
        </div><p className="mt-2 text-[10px] leading-relaxed text-[#8a918c]">Enter to send · Shift + Enter for a new line · results retain the agent’s markdown context.</p>
      </div>
    </section>
  );
}
