import React, { useState } from "react";
import { Send, Loader2 } from "lucide-react";

const STRATEGIES = ["auto", "cost", "quality", "latency", "manual"];

export default function PromptBox({ onSend, sending }) {
  const [text, setText] = useState("");
  const [strategy, setStrategy] = useState("auto");

  const submit = (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    onSend(text.trim(), strategy);
    setText("");
  };

  return (
    <form onSubmit={submit} className="bg-panel border border-line rounded-md p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] text-muted font-mono uppercase tracking-wide">Send a real request</span>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="ml-auto bg-panel2 border border-line rounded-md text-[11px] font-mono text-muted px-2 py-1 focus:outline-none"
        >
          {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask something — e.g. What is the capital of Japan?"
          className="flex-1 bg-panel2 border border-line rounded-md px-3 py-2 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-blue/50"
          disabled={sending}
        />
        <button
          type="submit"
          disabled={sending || !text.trim()}
          className="bg-blue/10 border border-blue/40 text-blue px-4 rounded-md hover:bg-blue/20 transition-colors disabled:opacity-40 flex items-center justify-center"
        >
          {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
        </button>
      </div>
    </form>
  );
}

