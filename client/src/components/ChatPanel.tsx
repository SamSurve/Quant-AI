/** Analyst's Ledger visual contract: conversational intelligence is organized like a compact research memo. */

import { ArrowUp, Bot, LoaderCircle, MessageSquareText, SendHorizontal, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Streamdown } from "streamdown";
import { cn } from "@/lib/utils";

/** Research Observatory visual contract: conversation remains a secondary research instrument, never the hero over sourced evidence. */

export type ChatMessage = { id: string; role: "user" | "agent"; content: string; pending?: boolean };

const prompts = ["Pressure-test the thesis", "Trace the source lane", "Separate evidence from interpretation"];

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
      <div className="relative flex items-center justify-between border-b border-[var(--rule)] px-5 py-4">
        <span className="absolute bottom-0 left-5 h-0.5 w-10 bg-[var(--research-indigo)]" />
        <div className="flex items-center gap-2.5">
          <span className="ledger-aperture grid size-8 place-items-center bg-[var(--surface-subtle)] text-[var(--research-indigo)]">
            <MessageSquareText className="size-3.5" />
          </span>
          <div>
            <p className="ledger-label">Conversational intelligence</p>
            <h2 className="mt-0.5 font-serif text-lg tracking-[-0.03em] text-[var(--ink)]">Research desk exchange</h2>
          </div>
        </div>
        <span className={cn("border px-1.5 py-1 text-[9px] font-bold uppercase tracking-[0.12em]", disabled ? "border-[color-mix(in_oklab,var(--negative)_42%,var(--rule))] text-[var(--negative)]" : "border-[color-mix(in_oklab,var(--provenance)_40%,var(--rule))] text-[var(--provenance)]")}>{disabled ? "Desk offline" : "Evidence lane"}</span>
      </div>

      <div className="flex items-center justify-between border-b border-[var(--rule)] bg-[var(--surface-raised)] px-5 py-2 text-[9px] font-bold uppercase tracking-[0.12em] text-[var(--ink-faint)]"><span>Session ledger</span><span>{messages.length ? `${Math.ceil(messages.length / 2)} research turn${messages.length > 2 ? "s" : ""}` : "No active brief"}</span></div>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
        {messages.length === 0 ? (
          <div className="border border-[var(--rule)] bg-[var(--surface-raised)] p-4">
            <div className="flex items-center gap-2 text-[var(--ink)]">
              <Bot className="size-4 text-[var(--provenance)]" />
            <p className="text-sm font-medium">Open a research ledger with QuantAI.</p>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-[var(--ink-soft)]">Frame an analyst action: pressure-test a thesis, trace a source lane, or request a sourced market update.</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={cn("flex gap-2.5", message.role === "user" && "justify-end")}>
              {message.role === "agent" && <Bot className="mt-1 size-4 shrink-0 text-[var(--provenance)]" />}
              <div
                className={cn(
                  "max-w-[90%] text-sm leading-relaxed",
                  message.role === "user" ? "rounded-sm bg-[var(--research-indigo)] px-3.5 py-2.5 text-[var(--primary-foreground)]" : "agent-markdown text-[var(--ink-soft)]",
                )}
              >
                {message.pending ? <LoaderCircle className="size-4 animate-spin text-[var(--research-indigo)]" /> : message.role === "agent" ? <Streamdown>{message.content}</Streamdown> : message.content}
              </div>
              {message.role === "user" && <UserRound className="mt-1 size-4 shrink-0 text-[var(--ink-faint)]" />}
            </div>
          ))
        )}
      </div>

      <div className="border-t border-[var(--rule)] bg-[var(--surface-raised)] p-4">
        <div className="mb-3"><p className="ledger-label mb-2">Research prompts</p><div className="flex gap-2 overflow-x-auto pb-1">
          {prompts.map((prompt) => (
            <button key={prompt} type="button" onClick={() => submit(prompt)} disabled={disabled || isLoading} className="whitespace-nowrap border-b border-[var(--rule-strong)] pb-1 text-[11px] font-semibold text-[var(--ink-soft)] transition-colors hover:border-[var(--research-indigo)] hover:text-[var(--research-indigo)] disabled:opacity-40">
              {prompt}
            </button>
          ))}</div></div>
        <div className="flex items-end gap-2 rounded-sm border border-[var(--rule-strong)] bg-[var(--surface)] p-1.5 focus-within:border-[var(--research-indigo)]">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={disabled ? "Connect AgentOS to open the research lane" : "Frame a research instruction…"}
            disabled={disabled || isLoading}
            rows={2}
            className="min-h-[42px] flex-1 resize-none bg-transparent px-2 py-1 text-sm text-[var(--ink)] outline-none placeholder:text-[var(--ink-faint)] disabled:cursor-not-allowed"
          />
          <button type="button" onClick={() => submit()} disabled={!draft.trim() || disabled || isLoading} className="grid size-9 shrink-0 place-items-center rounded-sm bg-[var(--research-indigo)] text-[var(--primary-foreground)] transition-all duration-150 hover:brightness-110 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45" aria-label="Send message">
            {isLoading ? <LoaderCircle className="size-4 animate-spin" /> : <SendHorizontal className="size-4" />}
          </button>
        </div><p className="mt-2 text-[10px] leading-relaxed text-[var(--ink-faint)]">Enter to send · Shift + Enter for a new line · trace factual values to the source lane before acting.</p>
      </div>
    </section>
  );
}
