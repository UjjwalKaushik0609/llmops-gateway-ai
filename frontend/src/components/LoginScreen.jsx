import React, { useEffect, useState } from "react";
import { Activity, LogIn, UserPlus, ShieldCheck, Route, Scissors, Brain, Cpu, Scale, FileCheck, Github } from "lucide-react";
import { login, register } from "../lib/api";

const STAGES = [
  { label: "Security",    icon: ShieldCheck, color: "#3DD68C" },
  { label: "Router",      icon: Route,       color: "#5B8DEF" },
  { label: "Token Opt",   icon: Scissors,    color: "#9B7BF5" },
  { label: "Memory",      icon: Brain,       color: "#F0A742" },
  { label: "Executor",    icon: Cpu,         color: "#3DD68C" },
  { label: "Evaluator",   icon: Scale,       color: "#9B7BF5" },
  { label: "Post-process",icon: FileCheck,   color: "#5B8DEF" },
];

const SAMPLE_LINES = [
  { text: "POST /api/v1/llm/complete",                              tone: "muted" },
  { text: "→ security_agent: risk_score=0.0",                      tone: "signal" },
  { text: "→ router_agent: provider=gemini model=gemini-2.5-flash", tone: "blue" },
  { text: "→ token_agent: compressed=false",                        tone: "violet" },
  { text: "→ executor_agent: latency=1805ms",                       tone: "signal" },
  { text: "→ evaluator_agent: faithfulness=0.95",                   tone: "violet" },
  { text: "← 200 OK · cost=$0.0000028",                            tone: "signal" },
];

const TONE_COLOR = { muted: "#7C8896", signal: "#3DD68C", blue: "#5B8DEF", violet: "#9B7BF5" };

function PipelinePreview() {
  const [activeIdx, setActiveIdx] = useState(-1);
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    let stageTimer, lineTimer, restartTimer;
    const run = () => {
      let i = 0;
      setVisibleLines(0);
      stageTimer = setInterval(() => {
        setActiveIdx(i++);
        if (i >= STAGES.length) { clearInterval(stageTimer); setTimeout(() => setActiveIdx(-1), 500); }
      }, 420);
      let j = 0;
      lineTimer = setInterval(() => {
        setVisibleLines(++j);
        if (j >= SAMPLE_LINES.length) clearInterval(lineTimer);
      }, 420);
      restartTimer = setTimeout(run, 420 * (STAGES.length + 3) + 1800);
    };
    run();
    return () => { clearInterval(stageTimer); clearInterval(lineTimer); clearTimeout(restartTimer); };
  }, []);

  return (
    <div className="relative h-full flex flex-col justify-center px-10 py-12 overflow-hidden">
      <div className="absolute inset-0 opacity-[0.07]"
        style={{ backgroundImage: "linear-gradient(#5B8DEF 1px, transparent 1px), linear-gradient(90deg, #5B8DEF 1px, transparent 1px)", backgroundSize: "28px 28px" }} />
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-transparent via-transparent to-bg pointer-events-none" />
      <div className="relative z-10 max-w-md">
        <div className="flex items-center gap-2 mb-1">
          <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full rounded-full bg-signal pulse-dot" /></span>
          <span className="text-[11px] font-mono text-muted uppercase tracking-wider">live agent pipeline</span>
        </div>
        <h2 className="text-[22px] font-semibold text-text leading-tight mb-2">Seven agents.<br />One routing decision.</h2>
        <p className="text-[13px] text-muted leading-relaxed mb-8">
          Every request is scanned, routed, optimized, executed, and judged for faithfulness — fully orchestrated by LangGraph.
        </p>
        <div className="flex items-center gap-1 mb-7 overflow-x-auto pb-1">
          {STAGES.map((s, i) => {
            const isActive = i === activeIdx;
            const Icon = s.icon;
            return (
              <React.Fragment key={s.label}>
                <div className="flex flex-col items-center gap-1.5 shrink-0 w-[60px]">
                  <div className="w-8 h-8 rounded-md flex items-center justify-center border transition-all duration-300"
                    style={{ borderColor: isActive ? s.color : "#232A35", backgroundColor: isActive ? `${s.color}1A` : "#171C25", boxShadow: isActive ? `0 0 0 1px ${s.color}40` : "none" }}>
                    <Icon size={14} style={{ color: isActive ? s.color : "#7C8896" }} />
                  </div>
                  <span className="text-[9px] font-mono text-center leading-tight" style={{ color: isActive ? "#E8EAED" : "#7C8896" }}>{s.label}</span>
                </div>
                {i < STAGES.length - 1 && <div className="flex-1 h-px bg-line min-w-[8px] -mt-4" />}
              </React.Fragment>
            );
          })}
        </div>
        <div className="bg-panel/60 border border-line rounded-md p-4 font-mono text-[11.5px] leading-relaxed min-h-[180px]">
          {SAMPLE_LINES.slice(0, visibleLines).map((line, i) => (
            <div key={i} className="row-in" style={{ color: TONE_COLOR[line.tone] }}>{line.text}</div>
          ))}
          {visibleLines < SAMPLE_LINES.length && <span className="inline-block w-1.5 h-3 bg-signal/70 animate-pulse ml-0.5" />}
        </div>
      </div>
    </div>
  );
}

export default function LoginScreen({ onLoggedIn }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") { await register(name, email, password); }
      await login(email, password);
      onLoggedIn();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Something went wrong. Check the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden lg:block border-r border-line bg-panel/30"><PipelinePreview /></div>
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-3 mb-9">
            <div className="w-9 h-9 rounded-md bg-signal/10 border border-signal/30 flex items-center justify-center">
              <Activity size={18} className="text-signal" />
            </div>
            <div>
              <h1 className="text-[16px] font-semibold tracking-tight leading-none">LLMOps Gateway</h1>
              <p className="text-[11px] text-muted font-mono leading-none mt-0.5">multi-llm routing console</p>
            </div>
          </div>
          <div className="bg-panel border border-line rounded-md p-6">
            <div className="flex gap-1 mb-5 bg-panel2 rounded-md p-1">
              {["login", "register"].map(m => (
                <button key={m} type="button" onClick={() => setMode(m)}
                  className={`flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors capitalize ${mode === m ? "bg-line text-text" : "text-muted hover:text-text"}`}>
                  {m === "login" ? "Log in" : "Register"}
                </button>
              ))}
            </div>
            <form onSubmit={handleSubmit} className="space-y-3">
              {mode === "register" && (
                <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} required
                  className="w-full bg-panel2 border border-line rounded-md px-3 py-2.5 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-signal/50 transition-colors" />
              )}
              <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email"
                className="w-full bg-panel2 border border-line rounded-md px-3 py-2.5 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-signal/50 transition-colors" />
              <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8}
                className="w-full bg-panel2 border border-line rounded-md px-3 py-2.5 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-signal/50 transition-colors" />
              {error && <div className="bg-red/10 border border-red/30 rounded-md px-3 py-2"><p className="text-[12px] text-red font-mono">{error}</p></div>}
              <button type="submit" disabled={loading}
                className="w-full bg-signal/10 border border-signal/40 text-signal text-[13px] font-medium py-2.5 rounded-md hover:bg-signal/20 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mt-1">
                {loading ? <span className="w-3.5 h-3.5 border-2 border-signal/30 border-t-signal rounded-full animate-spin" />
                  : mode === "login" ? <LogIn size={14} /> : <UserPlus size={14} />}
                {loading ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
              </button>
            </form>
          </div>
          <div className="flex items-center justify-between mt-4 px-1">
            <p className="text-[11px] text-muted font-mono">connects to localhost:8000</p>
            <a href="https://github.com" className="flex items-center gap-1 text-[11px] text-muted hover:text-text transition-colors">
              <Github size={12} /> source
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}


