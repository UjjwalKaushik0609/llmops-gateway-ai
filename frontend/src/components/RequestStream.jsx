import React from "react";
import { ShieldCheck, ShieldAlert, Zap, AlertTriangle } from "lucide-react";
import { PROVIDER_COLORS } from "../lib/demoData";

const STATUS_CONFIG = {
  success: { color: "#3DD68C", label: "OK" },
  blocked: { color: "#FF5C5C", label: "BLOCKED" },
  error:   { color: "#F0A742", label: "ERROR" },
};

function timeAgo(date) {
  const s = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (s < 1) return "now";
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s / 60)}m ago`;
}

function Row({ r }) {
  const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.error;
  return (
    <div className="row-in grid grid-cols-[16px_1fr_90px_70px_60px_70px] items-center gap-3 px-4 py-2.5 border-b border-line/60 hover:bg-panel2/60 transition-colors">
      <div className="flex justify-center">
        {r.status === "blocked"
          ? <ShieldAlert size={13} style={{ color: cfg.color }} />
          : r.status === "error"
          ? <AlertTriangle size={13} style={{ color: cfg.color }} />
          : <ShieldCheck size={13} style={{ color: cfg.color }} />}
      </div>
      <div className="min-w-0">
        <div className="text-[13px] text-text truncate font-medium">{r.prompt}</div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-[10px] font-mono font-semibold px-1.5 py-px rounded-sm"
            style={{ color: PROVIDER_COLORS[r.provider] || "#7C8896", backgroundColor: `${PROVIDER_COLORS[r.provider] || "#7C8896"}1A` }}>
            {r.provider}
          </span>
          <span className="text-[10px] font-mono text-muted">{r.model}</span>
          <span className="text-[10px] font-mono text-muted">· via {r.strategy}</span>
        </div>
      </div>
      <div className="text-right font-mono text-[12px] text-muted">
        {r.tokensIn}<span className="text-line">/</span>{r.tokensOut}<span className="text-muted/60"> tok</span>
      </div>
      <div className="text-right font-mono text-[12px]">
        <span className={r.latencyMs > 1800 ? "text-amber" : "text-muted"}>{r.latencyMs}ms</span>
      </div>
      <div className="text-right font-mono text-[12px] text-text">${r.costUsd.toFixed(4)}</div>
      <div className="text-right text-[11px] font-mono text-muted">{timeAgo(r.timestamp)}</div>
    </div>
  );
}

export default function RequestStream({ feed }) {
  return (
    <div className="bg-panel border border-line rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-line">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-signal pulse-dot" />
          </span>
          <h2 className="text-[13px] font-semibold tracking-wide">REQUEST STREAM</h2>
          <span className="text-[11px] text-muted font-mono">/ live agent pipeline output</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-muted font-mono">
          <Zap size={12} />
          security → router → token-opt → memory → executor → evaluator
        </div>
      </div>
      <div className="grid grid-cols-[16px_1fr_90px_70px_60px_70px] gap-3 px-4 py-2 border-b border-line bg-panel2/40 text-[10px] font-mono uppercase tracking-wider text-muted">
        <div></div>
        <div>request</div>
        <div className="text-right">tokens</div>
        <div className="text-right">latency</div>
        <div className="text-right">cost</div>
        <div className="text-right">when</div>
      </div>
      <div className="max-h-[420px] overflow-y-auto">
        {feed.length === 0
          ? <p className="text-[12px] text-muted font-mono px-4 py-6 text-center">No requests yet — send one above.</p>
          : feed.map((r) => <Row key={r.id} r={r} />)}
      </div>
    </div>
  );
}

