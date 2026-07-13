import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { PROVIDER_COLORS } from "../lib/demoData";

export default function ProviderDonut({ byProvider }) {
  const data = Object.entries(byProvider)
    .map(([name, v]) => ({ name, value: v.requests, cost: v.cost }))
    .filter((d) => d.value > 0);
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="bg-panel border border-line rounded-md p-4 h-full flex flex-col">
      <h2 className="text-[13px] font-semibold tracking-wide mb-1">PROVIDER ROUTING</h2>
      <p className="text-[11px] text-muted font-mono mb-2">share of requests</p>
      <div className="relative flex-1 min-h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="92%" paddingAngle={3} stroke="none">
              {data.map((d) => (
                <Cell key={d.name} fill={PROVIDER_COLORS[d.name] || "#7C8896"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: "#171C25", border: "1px solid #232A35", borderRadius: 6, fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}
              formatter={(value, name) => [`${value} req`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="font-mono text-2xl font-semibold">{total}</span>
          <span className="text-[10px] text-muted uppercase tracking-wide">requests</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-2 text-[11px]">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: PROVIDER_COLORS[d.name] || "#7C8896" }} />
            <span className="font-mono text-muted capitalize truncate">{d.name}</span>
            <span className="font-mono text-text ml-auto">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
