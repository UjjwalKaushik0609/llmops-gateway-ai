import React from "react";

const TONE_STYLES = {
  neutral: "text-text",
  signal:  "text-signal",
  amber:   "text-amber",
  red:     "text-red",
  blue:    "text-blue",
  violet:  "text-violet",
};

export default function StatCard({ label, value, sub, tone = "neutral", icon: Icon }) {
  return (
    <div className="bg-panel border border-line rounded-md px-4 py-3 flex flex-col gap-1.5 min-w-0">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium tracking-wide text-muted uppercase">{label}</span>
        {Icon && <Icon size={14} className="text-muted" strokeWidth={2} />}
      </div>
      <div className={`font-mono text-2xl font-semibold leading-none ${TONE_STYLES[tone]}`}>{value}</div>
      {sub && <div className="text-[11px] text-muted font-mono">{sub}</div>}
    </div>
  );
}
