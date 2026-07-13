import React, { useMemo } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function CostTrend({ feed }) {
  const data = useMemo(() => {
    const buckets = [];
    const bucketSize = Math.max(1, Math.floor(feed.length / 12));
    for (let i = 0; i < feed.length; i += bucketSize) {
      const slice = feed.slice(i, i + bucketSize);
      const cost = slice.reduce((s, r) => s + r.costUsd, 0);
      buckets.push({ idx: buckets.length, cost: Number(cost.toFixed(4)) });
    }
    return buckets.length ? buckets : [{ idx: 0, cost: 0 }];
  }, [feed]);

  return (
    <div className="bg-panel border border-line rounded-md p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-[13px] font-semibold tracking-wide">COST OVER TIME</h2>
          <p className="text-[11px] text-muted font-mono">USD spend per interval</p>
        </div>
      </div>
      <div className="h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5B8DEF" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#5B8DEF" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#232A35" strokeDasharray="2 4" />
            <XAxis dataKey="idx" hide />
            <YAxis tick={{ fill: "#7C8896", fontSize: 10, fontFamily: "JetBrains Mono" }} tickFormatter={(v) => `$${v}`} width={48} />
            <Tooltip
              contentStyle={{ backgroundColor: "#171C25", border: "1px solid #232A35", borderRadius: 6, fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}
              formatter={(v) => [`$${v}`, "cost"]}
              labelFormatter={() => ""}
            />
            <Area type="monotone" dataKey="cost" stroke="#5B8DEF" strokeWidth={2} fill="url(#costFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

