import React from "react";
import { ShieldCheck, Route, Scissors, Brain, Cpu, FileCheck, Scale } from "lucide-react";

const STAGES = [
  { key: "security",  label: "Security",     icon: ShieldCheck, color: "#3DD68C" },
  { key: "router",    label: "Router",        icon: Route,       color: "#5B8DEF" },
  { key: "token",     label: "Token Opt",     icon: Scissors,    color: "#9B7BF5" },
  { key: "memory",    label: "Memory",        icon: Brain,       color: "#F0A742" },
  { key: "executor",  label: "Executor",      icon: Cpu,         color: "#3DD68C" },
  { key: "evaluator", label: "Evaluator",     icon: Scale,       color: "#9B7BF5" },
  { key: "post",      label: "Post-process",  icon: FileCheck,   color: "#5B8DEF" },
];

export default function PipelineDiagram({ activeIdx = -1 }) {
  return (
    <div className="bg-panel border border-line rounded-md p-4">
      <h2 className="text-[13px] font-semibold tracking-wide mb-1">AGENT PIPELINE</h2>
      <p className="text-[11px] text-muted font-mono mb-4">
        LangGraph StateGraph · 7 nodes · sequential with conditional gates
      </p>
      <div className="flex items-center overflow-x-auto pb-1">
        {STAGES.map((s, i) => {
          const isActive = i === activeIdx;
          const Icon = s.icon;
          return (
            <React.Fragment key={s.key}>
              <div className="flex flex-col items-center gap-2 shrink-0 w-[92px]">
                <div
                  className="w-9 h-9 rounded-md flex items-center justify-center border transition-all duration-300"
                  style={{
                    borderColor: isActive ? s.color : "#232A35",
                    backgroundColor: isActive ? `${s.color}1A` : "#171C25",
                    boxShadow: isActive ? `0 0 0 1px ${s.color}40` : "none",
                  }}
                >
                  <Icon size={16} style={{ color: isActive ? s.color : "#7C8896" }} />
                </div>
                <span className="text-[10px] font-mono text-center leading-tight"
                  style={{ color: isActive ? "#E8EAED" : "#7C8896" }}>
                  {s.label}
                </span>
              </div>
              {i < STAGES.length - 1 && (
                <div className="flex-1 h-px bg-line min-w-[16px] relative -mt-5">
                  {isActive && (
                    <div className="absolute inset-0 overflow-hidden">
                      <div className="h-px w-1/3 scan-line" style={{ backgroundColor: s.color }} />
                    </div>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

