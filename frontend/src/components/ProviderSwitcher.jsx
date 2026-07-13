import React, { useEffect, useState, useRef } from "react";
import { ChevronDown, Check, Zap, AlertCircle, HelpCircle } from "lucide-react";
import api from "../lib/api";

const PROVIDER_COLORS = {
  gemini:     "#3DD68C",
  openai:     "#5B8DEF",
  anthropic:  "#9B7BF5",
  groq:       "#F0A742",
  mistral:    "#5B8DEF",
  together:   "#9B7BF5",
  openrouter: "#3DD68C",
  ollama:     "#F0A742",
  custom:     "#7C8896",
};

const PROVIDER_LABELS = {
  gemini:     "Gemini",
  openai:     "OpenAI",
  anthropic:  "Anthropic",
  groq:       "Groq",
  mistral:    "Mistral",
  together:   "Together AI",
  openrouter: "OpenRouter",
  ollama:     "Ollama",
  custom:     "Custom API",
};

export default function ProviderSwitcher({ selected, onSelect }) {
  const [open, setOpen] = useState(false);
  const [providers, setProviders] = useState([]);
  const ref = useRef(null);

  useEffect(() => {
    api.get("/providers/").then(r => {
      setProviders(r.data || []);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const current = providers.find(p => p.provider === selected);
  const color = PROVIDER_COLORS[selected] || "#7C8896";
  const enabledProviders = providers.filter(p => p.enabled);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 bg-panel2 border border-line rounded-md px-3 py-1.5 hover:border-line/80 transition-colors"
      >
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full"
            style={{ backgroundColor: color,
                     animation: current?.health_status === "healthy" ? "pulse-dot 2s infinite" : "none" }} />
        </span>
        <span className="text-[11px] font-mono" style={{ color }}>
          {PROVIDER_LABELS[selected] || selected}
        </span>
        {current?.selected_model && (
          <span className="text-[10px] text-muted font-mono hidden sm:inline">
            {current.selected_model.split("/").pop().slice(0, 20)}
          </span>
        )}
        <ChevronDown size={12} className="text-muted" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-64 bg-panel border border-line rounded-md shadow-xl z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-line">
            <p className="text-[10px] font-mono text-muted uppercase tracking-wide">Switch Provider</p>
            <p className="text-[10px] text-muted mt-0.5">No restart required</p>
          </div>

          <div className="py-1 max-h-[300px] overflow-y-auto">
            {enabledProviders.length === 0 ? (
              <p className="text-[12px] text-muted px-3 py-2">No providers configured. Open Provider Settings.</p>
            ) : (
              enabledProviders.map(p => {
                const pColor = PROVIDER_COLORS[p.provider] || "#7C8896";
                const isSelected = p.provider === selected;
                return (
                  <button
                    key={p.provider}
                    onClick={() => { onSelect(p.provider); setOpen(false); }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-panel2 transition-colors text-left ${isSelected ? "bg-panel2" : ""}`}
                  >
                    <span className="relative flex h-2 w-2 shrink-0">
                      <span className="absolute inline-flex h-full w-full rounded-full"
                        style={{ backgroundColor: p.health_status === "healthy" ? pColor : p.health_status === "error" ? "#FF5C5C" : "#7C8896" }} />
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[12px] font-medium" style={{ color: isSelected ? pColor : undefined }}>
                          {PROVIDER_LABELS[p.provider] || p.provider}
                        </span>
                        {isSelected && <Check size={11} style={{ color: pColor }} />}
                      </div>
                      {p.selected_model && (
                        <p className="text-[10px] text-muted font-mono truncate">{p.selected_model}</p>
                      )}
                    </div>

                    <div className="text-right shrink-0">
                      {p.health_status === "healthy" && p.last_latency_ms && (
                        <span className="text-[10px] font-mono text-signal flex items-center gap-0.5">
                          <Zap size={8} /> {p.last_latency_ms}ms
                        </span>
                      )}
                      {p.health_status === "error" && (
                        <AlertCircle size={11} className="text-red" />
                      )}
                      {p.health_status === "unknown" && (
                        <HelpCircle size={11} className="text-muted" />
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="border-t border-line px-3 py-2">
            <p className="text-[10px] text-muted font-mono">
              {enabledProviders.filter(p => p.health_status === "healthy").length}/{enabledProviders.length} healthy
            </p>
          </div>
        </div>
      )}
    </div>
  );
}