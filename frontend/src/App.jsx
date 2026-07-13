import React, { useEffect, useRef, useState } from "react";
import { Activity, DollarSign, Gauge, ShieldAlert, Database, LogOut, Settings, AlertCircle } from "lucide-react";
import StatCard from "./components/StatCard";
import RequestStream from "./components/RequestStream";
import ProviderDonut from "./components/ProviderDonut";
import CostTrend from "./components/CostTrend";
import PipelineDiagram from "./components/PipelineDiagram";
import LoginScreen from "./components/LoginScreen";
import PromptBox from "./components/PromptBox";
import ProviderSettings from "./components/ProviderSettings";
import ProviderSwitcher from "./components/ProviderSwitcher";
import SetupWizard from "./components/SetupWizard";
import { isLoggedIn, logout, completeLLM, getRequestHistory } from "./lib/api";
import { PROVIDER_COLORS } from "./lib/demoData";
import api from "./lib/api";

const STAGE_NAMES = ["security", "router", "token", "memory", "executor", "evaluator", "post"];
const POLL_INTERVAL_MS = 5000;

function mapHistoryToFeed(requests) {
  return requests.map((r) => ({
    id: r.id,
    provider: r.provider,
    model: r.model,
    strategy: r.routing_strategy || "auto",
    prompt: "Request #" + r.id.slice(0, 8),
    status: r.status === "success" ? "success" : r.status === "blocked" ? "blocked" : "error",
    latencyMs: r.latency_ms,
    tokensIn: r.tokens_input,
    tokensOut: r.tokens_output,
    costUsd: r.cost_usd,
    timestamp: new Date(r.timestamp),
  }));
}

function buildSummary(feed) {
  const totalRequests = feed.length;
  const totalCost = feed.reduce((s, r) => s + r.costUsd, 0);
  const totalTokens = feed.reduce((s, r) => s + r.tokensIn + r.tokensOut, 0);
  const avgLatency = feed.reduce((s, r) => s + r.latencyMs, 0) / (feed.length || 1);
  const blocks = feed.filter((r) => r.status === "blocked").length;
  const errors = feed.filter((r) => r.status === "error").length;
  const byProvider = {};
  for (const p of Object.keys(PROVIDER_COLORS)) {
    const subset = feed.filter((r) => r.provider === p);
    byProvider[p] = {
      requests: subset.length,
      cost: subset.reduce((s, r) => s + r.costUsd, 0),
    };
  }
  return { totalRequests, totalCost, totalTokens, avgLatency, blocks, errors, byProvider };
}

function Dashboard({ onLogout }) {
  const [feed, setFeed] = useState([]);
  const [activeStage, setActiveStage] = useState(-1);
  const [sending, setSending] = useState(false);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [securityBlock, setSecurityBlock] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [activeProvider, setActiveProvider] = useState("gemini");
  const stageTimer = useRef(null);

  const summary = buildSummary(feed);

  const refreshHistory = async () => {
    try {
      const res = await getRequestHistory(1);
      setFeed(mapHistoryToFeed(res.data.requests || []));
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  useEffect(() => {
    refreshHistory();
    const interval = setInterval(refreshHistory, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const animatePipeline = () => {
    let i = 0;
    clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => {
      setActiveStage(i);
      i++;
      if (i >= STAGE_NAMES.length) {
        clearInterval(stageTimer.current);
        setTimeout(() => setActiveStage(-1), 400);
      }
    }, 220);
  };

  const handleSend = async (text, strategy) => {
    setSending(true);
    setSecurityBlock(null);
    setLastAnswer(null);
    animatePipeline();
    try {
    const res = await completeLLM({
    messages: [{ role: "user", content: text }],
    routing_strategy: strategy,
    provider: activeProvider,
    model: activeProvider === "gemini" ? "gemini-2.5-flash" : undefined,
  });

      setLastAnswer(res.data);
      await refreshHistory();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const isSecurityBlock = err.response?.status === 400 && detail && typeof detail === "object" && Array.isArray(detail.flags);
      if (isSecurityBlock) {
        setSecurityBlock(detail);
      } else {
        setSecurityBlock({ error: detail || "Request failed", flags: [] });
      }
      await refreshHistory();
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen px-6 py-6 max-w-[1400px] mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-signal/10 border border-signal/30 flex items-center justify-center">
            <Activity size={16} className="text-signal" />
          </div>
          <div>
            <h1 className="text-[15px] font-semibold tracking-tight leading-none">LLMOps Gateway</h1>
            <p className="text-[11px] text-muted font-mono leading-none mt-0.5">live · connected to localhost:8000</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ProviderSwitcher selected={activeProvider} onSelect={setActiveProvider} />
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-1.5 text-[12px] text-muted hover:text-text transition-colors border border-line rounded-md px-2.5 py-1.5"
          >
            <Settings size={13} /> Providers
          </button>
          <button
            onClick={() => { logout(); onLogout(); }}
            className="flex items-center gap-1.5 text-[12px] text-muted hover:text-text transition-colors border border-line rounded-md px-2.5 py-1.5"
          >
            <LogOut size={13} /> log out
          </button>
        </div>
      </header>

      {showSettings && <ProviderSettings onClose={() => setShowSettings(false)} />}

      <div className="mb-5">
        <PromptBox onSend={handleSend} sending={sending} />
      </div>

      {lastAnswer && (
        <div className="mb-5 bg-panel border border-signal/30 rounded-md p-4">
          <div className="flex items-center gap-2 mb-2 text-[11px] font-mono text-muted uppercase tracking-wide">
            <span className="text-signal">●</span> response from {lastAnswer.provider} / {lastAnswer.model}
          </div>
          <p className="text-[14px] text-text leading-relaxed">{lastAnswer.content}</p>
          <div className="flex flex-wrap items-center gap-4 mt-3 text-[11px] font-mono text-muted">
            <span>{lastAnswer.tokens_input}/{lastAnswer.tokens_output} tok</span>
            <span>{lastAnswer.latency_ms}ms</span>
            <span>${lastAnswer.cost_usd.toFixed(6)}</span>
            <span>via {lastAnswer.routing_strategy}</span>
            {lastAnswer.metadata?.evaluation && !lastAnswer.metadata.evaluation.skipped && (
              <span
                className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm border"
                style={{
                  borderColor: lastAnswer.metadata.evaluation.score >= 0.8 ? "#3DD68C40" : lastAnswer.metadata.evaluation.score >= 0.5 ? "#F0A74240" : "#FF5C5C40",
                  color: lastAnswer.metadata.evaluation.score >= 0.8 ? "#3DD68C" : lastAnswer.metadata.evaluation.score >= 0.5 ? "#F0A742" : "#FF5C5C",
                }}
              >
                faithfulness {(lastAnswer.metadata.evaluation.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          {lastAnswer.metadata?.evaluation?.reasoning && !lastAnswer.metadata.evaluation.skipped && (
            <p className="text-[11px] text-muted font-mono mt-1.5 italic">
              judge: {lastAnswer.metadata.evaluation.reasoning}
            </p>
          )}
        </div>
      )}

      {securityBlock && (
        <div className="mb-5 bg-panel border rounded-md p-4" style={{ borderColor: securityBlock.flags?.length ? "rgba(255,77,79,0.2)" : "rgba(100,116,139,0.2)" }}>
          <div className="flex items-center gap-2 mb-2 text-[11px] font-mono uppercase tracking-wide" style={{ color: securityBlock.flags?.length ? "#FF5C5C" : "#7C8896" }}>
            {securityBlock.flags?.length ? <ShieldAlert size={13} /> : <AlertCircle size={13} />}
            {securityBlock.flags?.length ? "blocked by security agent" : "request failed"}
          </div>
          {securityBlock.flags?.length > 0 ? (
            <ul className="text-[12px] font-mono text-muted space-y-0.5">
              {securityBlock.flags.map((f, i) => <li key={i}>· {f}</li>)}
            </ul>
          ) : (
            <p className="text-[12px] font-mono text-muted">{securityBlock.error}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
        <StatCard label="Requests" value={summary.totalRequests} sub="all time" icon={Activity} />
        <StatCard label="Spend" value={`$${summary.totalCost.toFixed(5)}`} sub="total so far" tone="blue" icon={DollarSign} />
        <StatCard label="Avg Latency" value={`${Math.round(summary.avgLatency)}ms`} sub="across all requests" tone={summary.avgLatency > 1200 ? "amber" : "signal"} icon={Gauge} />
        <StatCard label="Blocked" value={summary.blocks} sub="prompt injection / PII" tone={summary.blocks > 0 ? "red" : "neutral"} icon={ShieldAlert} />
        <StatCard label="Tokens" value={summary.totalTokens.toLocaleString()} sub="input + output" tone="violet" icon={Database} />
      </div>

      <div className="mb-5">
        <PipelineDiagram activeIdx={activeStage} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 flex flex-col gap-5">
          <RequestStream feed={feed} />
          <CostTrend feed={feed} />
        </div>
        <div className="flex flex-col gap-5">
          <ProviderDonut byProvider={summary.byProvider} />
        </div>
      </div>

      <footer className="mt-8 pb-4 text-center text-[11px] text-muted font-mono">
        LLMOps Gateway AI · live data · {summary.totalRequests} requests tracked
      </footer>
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(isLoggedIn());
  const [setupDone, setSetupDone] = useState(null); // null = loading

  useEffect(() => {
    if (!loggedIn) {
      setSetupDone(true); // reset when logged out
      return;
    }
    api.get("/providers/setup/status")
      .then(r => setSetupDone(r.data.completed))
      .catch(() => setSetupDone(true)); // if check fails, skip wizard
  }, [loggedIn]);

  if (!loggedIn) {
    return <LoginScreen onLoggedIn={() => setLoggedIn(true)} />;
  }

  if (setupDone === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[12px] text-muted font-mono">Loading...</div>
      </div>
    );
  }

  if (!setupDone) {
    return <SetupWizard onComplete={() => setSetupDone(true)} />;
  }

  return <Dashboard onLogout={() => { setLoggedIn(false); setSetupDone(null); }} />;
}