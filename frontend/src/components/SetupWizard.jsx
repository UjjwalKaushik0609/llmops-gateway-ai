import React, { useState } from "react";
import { Activity, ChevronRight, ChevronLeft, Check, Loader2, Zap } from "lucide-react";
import api from "../lib/api";

const STEPS = ["Welcome", "Choose Providers", "Add Keys", "Test", "Launch"];

const ALL_PROVIDERS = [
  { id: "gemini",     label: "Google Gemini",    color: "#3DD68C", free: true,  note: "Free tier available" },
  { id: "openai",     label: "OpenAI",           color: "#5B8DEF", free: false, note: "GPT-4o, GPT-4o-mini" },
  { id: "anthropic",  label: "Anthropic Claude", color: "#9B7BF5", free: false, note: "Claude 3.5 Sonnet" },
  { id: "groq",       label: "Groq",             color: "#F0A742", free: true,  note: "Ultra-fast inference" },
  { id: "mistral",    label: "Mistral",          color: "#5B8DEF", free: true,  note: "Open-source models" },
  { id: "together",   label: "Together AI",      color: "#9B7BF5", free: false, note: "100+ open models" },
  { id: "openrouter", label: "OpenRouter",       color: "#3DD68C", free: false, note: "Unified API" },
  { id: "ollama",     label: "Ollama (Local)",   color: "#F0A742", free: true,  note: "No API key needed" },
  { id: "custom",     label: "Custom API",       color: "#7C8896", free: true,  note: "OpenAI-compatible" },
];

export default function SetupWizard({ onComplete }) {
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState(["gemini"]);
  const [keys, setKeys] = useState({});
  const [baseUrls, setBaseUrls] = useState({ ollama: "http://localhost:11434/v1" });
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});
  const [saving, setSaving] = useState(false);

  const toggleProvider = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
  };

  const testConnection = async (provider) => {
    setTesting(prev => ({ ...prev, [provider]: true }));
    try {
      const r = await api.post(`/providers/test/${provider}`);
      setTestResults(prev => ({ ...prev, [provider]: r.data }));
    } catch (err) {
      setTestResults(prev => ({ ...prev, [provider]: { connected: false, error: err.response?.data?.detail || "Failed" } }));
    } finally {
      setTesting(prev => ({ ...prev, [provider]: false }));
    }
  };

  const handleComplete = async () => {
    setSaving(true);
    try {
      for (const provider of selected) {
        const key = keys[provider];
        await api.post("/providers/save", {
          provider, enabled: true,
          api_key: key || null,
          base_url: baseUrls[provider] || null,
        });
      }
      await api.post("/providers/setup/complete", {
        providers: selected.map(p => ({ provider: p, enabled: true, api_key: keys[p] || null, base_url: baseUrls[p] || null }))
      });
      onComplete();
    } catch (err) {
      console.error("Setup failed", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-md bg-signal/10 border border-signal/30 flex items-center justify-center">
            <Activity size={20} className="text-signal" />
          </div>
          <div>
            <h1 className="text-[18px] font-semibold">LLMOps Gateway</h1>
            <p className="text-[11px] text-muted font-mono">first-time setup</p>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center gap-1">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-mono border transition-all ${
                  i < step ? "bg-signal border-signal text-bg" : i === step ? "border-signal text-signal" : "border-line text-muted"
                }`}>
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className={`text-[9px] font-mono uppercase tracking-wide ${i === step ? "text-text" : "text-muted"}`}>{s}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`h-px w-8 mb-4 ${i < step ? "bg-signal" : "bg-line"}`} />}
            </React.Fragment>
          ))}
        </div>

        <div className="bg-panel border border-line rounded-md p-6 mb-5">
          {step === 0 && (
            <div className="text-center">
              <div className="text-4xl mb-4">🚀</div>
              <h2 className="text-[18px] font-semibold mb-3">Welcome to LLMOps Gateway</h2>
              <p className="text-[13px] text-muted leading-relaxed mb-6">
                Set up your AI operating system — no code editing required. Connect your LLM providers in a few steps.
              </p>
              <div className="grid grid-cols-3 gap-3 text-left">
                {[
                  { icon: "🔐", title: "Secure",        desc: "Keys encrypted in database" },
                  { icon: "🔀", title: "Multi-Provider", desc: "9 providers, switch anytime" },
                  { icon: "🤖", title: "Smart Routing",  desc: "7 AI agents route every request" },
                ].map(f => (
                  <div key={f.title} className="bg-panel2 border border-line rounded-md p-3">
                    <div className="text-xl mb-1">{f.icon}</div>
                    <div className="text-[12px] font-semibold mb-0.5">{f.title}</div>
                    <div className="text-[11px] text-muted">{f.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div>
              <h2 className="text-[15px] font-semibold mb-1">Choose your providers</h2>
              <p className="text-[12px] text-muted mb-4">Select at least one. Add more later from Settings.</p>
              <div className="grid grid-cols-1 gap-2">
                {ALL_PROVIDERS.map(p => (
                  <label key={p.id} className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-all ${
                    selected.includes(p.id) ? "border-signal/40 bg-signal/5" : "border-line bg-panel2"
                  }`}>
                    <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggleProvider(p.id)} className="sr-only" />
                    <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${selected.includes(p.id) ? "bg-signal border-signal" : "border-line"}`}>
                      {selected.includes(p.id) && <Check size={10} className="text-bg" />}
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-sm shrink-0"
                      style={{ color: p.color, backgroundColor: `${p.color}1A` }}>{p.id}</span>
                    <span className="text-[13px] font-medium flex-1">{p.label}</span>
                    <span className="text-[11px] text-muted">{p.note}</span>
                    {p.free && <span className="text-[10px] text-signal border border-signal/30 rounded px-1.5 py-0.5 shrink-0">free</span>}
                  </label>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-[15px] font-semibold mb-1">Add your API keys</h2>
              <p className="text-[12px] text-muted mb-4">Keys are encrypted immediately — never stored in plain text.</p>
              <div className="space-y-4">
                {selected.map(pid => {
                  const meta = ALL_PROVIDERS.find(p => p.id === pid);
                  const needsUrl = ["ollama","custom","openrouter"].includes(pid);
                  return (
                    <div key={pid} className="bg-panel2 border border-line rounded-md p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded-sm"
                          style={{ color: meta?.color, backgroundColor: `${meta?.color}1A` }}>{pid}</span>
                        <span className="text-[13px] font-medium">{meta?.label}</span>
                      </div>
                      {pid !== "ollama" && (
                        <input type="password" placeholder={`${meta?.label} API key`}
                          value={keys[pid] || ""} onChange={e => setKeys(prev => ({ ...prev, [pid]: e.target.value }))}
                          className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[13px] font-mono placeholder:text-muted focus:outline-none focus:border-signal/50 mb-2" />
                      )}
                      {needsUrl && (
                        <input type="text" placeholder="Base URL (e.g. http://localhost:11434/v1)"
                          value={baseUrls[pid] || ""} onChange={e => setBaseUrls(prev => ({ ...prev, [pid]: e.target.value }))}
                          className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[12px] font-mono placeholder:text-muted focus:outline-none focus:border-signal/50" />
                      )}
                      {pid === "ollama" && <p className="text-[11px] text-muted font-mono">No API key required — just make sure Ollama is running locally.</p>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-[15px] font-semibold mb-1">Test connections</h2>
              <p className="text-[12px] text-muted mb-4">Verify each provider before launching.</p>
              <div className="space-y-2">
                {selected.map(pid => {
                  const meta = ALL_PROVIDERS.find(p => p.id === pid);
                  const result = testResults[pid];
                  const isTesting = testing[pid];
                  return (
                    <div key={pid} className="flex items-center gap-3 bg-panel2 border border-line rounded-md p-3">
                      <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-sm shrink-0"
                        style={{ color: meta?.color, backgroundColor: `${meta?.color}1A` }}>{pid}</span>
                      <span className="text-[12px] flex-1">{meta?.label}</span>
                      {result && (
                        <span className={`text-[11px] font-mono ${result.connected ? "text-signal" : "text-red"}`}>
                          {result.connected ? `✓ ${result.latency_ms}ms` : `✗ ${String(result.error || "").slice(0, 40)}`}
                        </span>
                      )}
                      <button onClick={() => testConnection(pid)} disabled={isTesting}
                        className="text-[11px] border border-line rounded-md px-2.5 py-1 text-muted hover:text-text transition-colors flex items-center gap-1 shrink-0">
                        {isTesting ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
                        {isTesting ? "Testing..." : "Test"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="text-center">
              <div className="text-4xl mb-4">🎉</div>
              <h2 className="text-[18px] font-semibold mb-3">You're all set!</h2>
              <p className="text-[13px] text-muted leading-relaxed mb-6">
                {selected.length} provider{selected.length !== 1 ? "s" : ""} configured. Keys encrypted and stored securely.
              </p>
              <div className="bg-panel2 border border-signal/20 rounded-md p-4 text-left">
                <p className="text-[12px] text-muted mb-2 font-mono uppercase tracking-wide">Configured providers:</p>
                <div className="flex flex-wrap gap-2">
                  {selected.map(pid => {
                    const meta = ALL_PROVIDERS.find(p => p.id === pid);
                    return (
                      <span key={pid} className="text-[11px] font-mono px-2 py-1 rounded-sm border"
                        style={{ color: meta?.color, borderColor: `${meta?.color}40`, backgroundColor: `${meta?.color}0D` }}>{pid}</span>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          <button onClick={() => setStep(s => s - 1)} disabled={step === 0}
            className="flex items-center gap-2 text-[12px] text-muted hover:text-text transition-colors disabled:opacity-30">
            <ChevronLeft size={14} /> Back
          </button>
          {step < STEPS.length - 1 ? (
            <button onClick={() => setStep(s => s + 1)} disabled={step === 1 && selected.length === 0}
              className="flex items-center gap-2 bg-signal/10 border border-signal/40 text-signal text-[13px] font-medium px-5 py-2 rounded-md hover:bg-signal/20 transition-colors disabled:opacity-40">
              {step === 0 ? "Get Started" : "Continue"} <ChevronRight size={14} />
            </button>
          ) : (
            <button onClick={handleComplete} disabled={saving}
              className="flex items-center gap-2 bg-signal/10 border border-signal/40 text-signal text-[13px] font-medium px-5 py-2 rounded-md hover:bg-signal/20 transition-colors disabled:opacity-40">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {saving ? "Saving..." : "Launch Dashboard"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

