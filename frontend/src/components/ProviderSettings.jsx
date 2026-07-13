import React, { useEffect, useState } from "react";
import {
  X, Zap, Trash2, Save, Check, Loader2, Plus,
  ChevronDown, ChevronUp, Shield, AlertCircle, HelpCircle
} from "lucide-react";
import api from "../lib/api";

const PROVIDERS = [
  { id: "gemini",     label: "Google Gemini",    color: "#3DD68C", keyPlaceholder: "AIzaSy...",      docsUrl: "https://aistudio.google.com/app/apikey" },
  { id: "openai",     label: "OpenAI",           color: "#5B8DEF", keyPlaceholder: "sk-...",          docsUrl: "https://platform.openai.com/api-keys" },
  { id: "anthropic",  label: "Anthropic Claude", color: "#9B7BF5", keyPlaceholder: "sk-ant-...",      docsUrl: "https://console.anthropic.com/settings/keys" },
  { id: "groq",       label: "Groq",             color: "#F0A742", keyPlaceholder: "gsk_...",         docsUrl: "https://console.groq.com/keys" },
  { id: "mistral",    label: "Mistral",          color: "#5B8DEF", keyPlaceholder: "...",             docsUrl: "https://console.mistral.ai/api-keys" },
  { id: "together",   label: "Together AI",      color: "#9B7BF5", keyPlaceholder: "...",             docsUrl: "https://api.together.xyz/settings/api-keys" },
  { id: "openrouter", label: "OpenRouter",       color: "#3DD68C", keyPlaceholder: "sk-or-...",       docsUrl: "https://openrouter.ai/keys" },
  { id: "ollama",     label: "Ollama (Local)",   color: "#F0A742", keyPlaceholder: null,              docsUrl: "https://ollama.ai" },
  { id: "custom",     label: "Custom API",       color: "#7C8896", keyPlaceholder: "optional key",   docsUrl: null },
];

const CONDITION_TYPES = [
  { value: "keyword",     label: "Prompt contains keyword" },
  { value: "token_count", label: "Token count exceeds" },
  { value: "cost_mode",   label: "Cost routing mode active" },
  { value: "always",      label: "Always (default provider)" },
];

function HealthDot({ status }) {
  const colors = { healthy: "#3DD68C", error: "#FF5C5C", unknown: "#7C8896" };
  return (
    <span className="relative flex h-2 w-2">
      <span className="absolute inline-flex h-full w-full rounded-full"
        style={{ backgroundColor: colors[status] || colors.unknown,
                 animation: status === "healthy" ? "pulse-dot 2s infinite" : "none" }} />
    </span>
  );
}

function ProviderCard({ config, onSave, onDelete, onTest }) {
  const meta = PROVIDERS.find(p => p.id === config.provider) || {};
  const [expanded, setExpanded] = useState(false);
  const [enabled, setEnabled] = useState(config.enabled);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(config.base_url || "");
  const [selectedModel, setSelectedModel] = useState(config.selected_model || "");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const handleSave = async () => {
    setSaving(true);
    await onSave({
      provider: config.provider,
      enabled,
      api_key: apiKey || undefined,
      base_url: baseUrl || undefined,
      selected_model: selectedModel || undefined,
    });
    setApiKey("");
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    const result = await onTest(config.provider);
    setTestResult(result);
    setTesting(false);
  };

  const needsBaseUrl = ["ollama", "custom", "openrouter"].includes(config.provider);
  const noKeyNeeded = config.provider === "ollama";

  return (
    <div className={`border rounded-md transition-all ${enabled ? "border-line" : "border-line/40 opacity-60"} bg-panel2`}>
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <HealthDot status={config.health_status} />
        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-sm shrink-0"
          style={{ color: meta.color, backgroundColor: `${meta.color}1A` }}>
          {config.provider}
        </span>
        <span className="text-[13px] font-medium flex-1">{meta.label}</span>

        {config.last_latency_ms && (
          <span className="text-[11px] font-mono text-muted">{config.last_latency_ms}ms</span>
        )}

        {config.masked_key && (
          <span className="text-[11px] font-mono text-muted flex items-center gap-1">
            <Shield size={10} /> {config.masked_key}
          </span>
        )}

        {/* Enable/Disable toggle */}
        <button
          onClick={() => setEnabled(e => !e)}
          className={`relative w-9 h-5 rounded-full transition-colors shrink-0 ${enabled ? "bg-signal/20 border border-signal/40" : "bg-panel border border-line"}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 rounded-full transition-all ${enabled ? "left-4 bg-signal" : "left-0.5 bg-muted"}`} />
        </button>

        <button onClick={() => setExpanded(e => !e)} className="text-muted hover:text-text transition-colors">
          {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {/* Expanded config */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-line pt-4 space-y-3">
          {/* API Key */}
          {!noKeyNeeded && (
            <div>
              <label className="text-[11px] font-mono text-muted uppercase tracking-wide block mb-1">
                API Key {config.has_key && <span className="text-signal ml-1">✓ saved</span>}
              </label>
              <input
                type="password"
                placeholder={config.has_key ? "Enter new key to replace existing" : meta.keyPlaceholder || "API key"}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[12px] font-mono placeholder:text-muted focus:outline-none focus:border-signal/50"
              />
              {meta.docsUrl && (
                <a href={meta.docsUrl} target="_blank" rel="noreferrer"
                  className="text-[10px] text-blue/70 hover:text-blue mt-1 block">
                  Get API key →
                </a>
              )}
            </div>
          )}

          {/* Base URL */}
          {needsBaseUrl && (
            <div>
              <label className="text-[11px] font-mono text-muted uppercase tracking-wide block mb-1">Base URL</label>
              <input
                type="text"
                placeholder={config.provider === "ollama" ? "http://localhost:11434/v1" : "https://..."}
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[12px] font-mono placeholder:text-muted focus:outline-none focus:border-signal/50"
              />
            </div>
          )}

          {/* Model selector */}
          {config.available_models?.length > 0 && (
            <div>
              <label className="text-[11px] font-mono text-muted uppercase tracking-wide block mb-1">Model</label>
              <select
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
                className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[12px] text-text focus:outline-none focus:border-signal/50"
              >
                {config.available_models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}

          {/* Last connected */}
          {config.last_connected_at && (
            <p className="text-[11px] text-muted font-mono">
              Last connected: {new Date(config.last_connected_at).toLocaleString()}
            </p>
          )}

          {/* Health message */}
          {config.health_message && config.health_status === "error" && (
            <div className="flex items-start gap-2 bg-red/5 border border-red/20 rounded-md px-3 py-2">
              <AlertCircle size={12} className="text-red shrink-0 mt-0.5" />
              <p className="text-[11px] text-red font-mono">{config.health_message}</p>
            </div>
          )}

          {/* Test result */}
          {testResult && (
            <div className={`flex items-start gap-2 rounded-md px-3 py-2 border ${
              testResult.connected ? "bg-signal/5 border-signal/20" : "bg-red/5 border-red/20"
            }`}>
              {testResult.connected
                ? <Check size={12} className="text-signal shrink-0 mt-0.5" />
                : <AlertCircle size={12} className="text-red shrink-0 mt-0.5" />}
              <p className="text-[11px] font-mono" style={{ color: testResult.connected ? "#3DD68C" : "#FF5C5C" }}>
                {testResult.connected
                  ? `Connected · ${testResult.latency_ms}ms`
                  : testResult.error?.slice(0, 80)}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <button onClick={handleTest} disabled={testing}
              className="flex items-center gap-1.5 text-[12px] border border-line rounded-md px-3 py-1.5 text-muted hover:text-text transition-colors">
              {testing ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
              Test Connection
            </button>
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-1.5 text-[12px] bg-signal/10 border border-signal/40 text-signal rounded-md px-3 py-1.5 hover:bg-signal/20 transition-colors">
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              Save
            </button>
            {config.has_key && (
              <button onClick={() => onDelete(config.provider)}
                className="ml-auto flex items-center gap-1.5 text-[12px] text-muted hover:text-red transition-colors">
                <Trash2 size={12} /> Delete Key
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function RoutingRulesSection() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newRule, setNewRule] = useState({
    name: "", condition_type: "keyword", condition_value: "",
    target_provider: "gemini", target_model: "", priority: 0,
  });

  const refresh = async () => {
    try {
      const r = await api.get("/providers/rules");
      setRules(r.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    try {
      await api.post("/providers/rules", newRule);
      setShowAdd(false);
      setNewRule({ name: "", condition_type: "keyword", condition_value: "", target_provider: "gemini", target_model: "", priority: 0 });
      await refresh();
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/providers/rules/${id}`);
      await refresh();
    } catch (e) { console.error(e); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-[13px] font-semibold">Auto-Routing Rules</h3>
          <p className="text-[11px] text-muted font-mono">Evaluated before standard routing strategy</p>
        </div>
        <button onClick={() => setShowAdd(s => !s)}
          className="flex items-center gap-1.5 text-[11px] border border-line rounded-md px-2.5 py-1.5 text-muted hover:text-text transition-colors">
          <Plus size={11} /> Add Rule
        </button>
      </div>

      {loading ? (
        <p className="text-[12px] text-muted font-mono">loading...</p>
      ) : rules.length === 0 && !showAdd ? (
        <div className="bg-panel2 border border-line rounded-md p-4 text-center">
          <p className="text-[12px] text-muted">No rules yet. Add rules to automatically route requests based on conditions.</p>
          <div className="mt-3 text-[11px] text-muted font-mono space-y-1 text-left max-w-sm mx-auto">
            <p>Example: <span className="text-signal">if prompt contains "code" → GPT-4o</span></p>
            <p>Example: <span className="text-blue">if tokens &gt; 15000 → Claude</span></p>
            <p>Example: <span className="text-violet">if cost mode → Gemini Flash</span></p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {rules.map(r => (
            <div key={r.id} className="flex items-center gap-3 bg-panel2 border border-line rounded-md px-3 py-2">
              <span className="text-[10px] font-mono bg-line px-1.5 py-0.5 rounded text-muted">#{r.priority}</span>
              <div className="flex-1 min-w-0">
                <span className="text-[12px] font-medium">{r.name}</span>
                <span className="text-[11px] text-muted font-mono ml-2">
                  {r.condition_type === "keyword" && `contains "${r.condition_value}"`}
                  {r.condition_type === "token_count" && `tokens > ${r.condition_value}`}
                  {r.condition_type === "cost_mode" && "when cost mode"}
                  {r.condition_type === "always" && "always"}
                  {" → "}{r.target_provider}{r.target_model ? `/${r.target_model}` : ""}
                </span>
              </div>
              <button onClick={() => handleDelete(r.id)} className="text-muted hover:text-red transition-colors">
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="mt-3 bg-panel2 border border-signal/20 rounded-md p-4 space-y-3">
          <input
            type="text"
            placeholder="Rule name (e.g. 'Code to GPT-4o')"
            value={newRule.name}
            onChange={e => setNewRule(p => ({ ...p, name: e.target.value }))}
            className="w-full bg-panel border border-line rounded-md px-3 py-2 text-[12px] placeholder:text-muted focus:outline-none focus:border-signal/50"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={newRule.condition_type}
              onChange={e => setNewRule(p => ({ ...p, condition_type: e.target.value }))}
              className="bg-panel border border-line rounded-md px-3 py-2 text-[12px] text-text focus:outline-none"
            >
              {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            {(newRule.condition_type === "keyword" || newRule.condition_type === "token_count") && (
              <input
                type="text"
                placeholder={newRule.condition_type === "keyword" ? "keyword" : "token limit (e.g. 15000)"}
                value={newRule.condition_value}
                onChange={e => setNewRule(p => ({ ...p, condition_value: e.target.value }))}
                className="bg-panel border border-line rounded-md px-3 py-2 text-[12px] font-mono placeholder:text-muted focus:outline-none focus:border-signal/50"
              />
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={newRule.target_provider}
              onChange={e => setNewRule(p => ({ ...p, target_provider: e.target.value }))}
              className="bg-panel border border-line rounded-md px-3 py-2 text-[12px] text-text focus:outline-none"
            >
              {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
            <input
              type="number"
              placeholder="Priority (0 = first)"
              value={newRule.priority}
              onChange={e => setNewRule(p => ({ ...p, priority: parseInt(e.target.value) || 0 }))}
              className="bg-panel border border-line rounded-md px-3 py-2 text-[12px] font-mono placeholder:text-muted focus:outline-none"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} disabled={!newRule.name}
              className="flex items-center gap-1.5 text-[12px] bg-signal/10 border border-signal/40 text-signal rounded-md px-3 py-1.5 hover:bg-signal/20 transition-colors disabled:opacity-40">
              <Check size={12} /> Add Rule
            </button>
            <button onClick={() => setShowAdd(false)}
              className="text-[12px] text-muted hover:text-text transition-colors px-3 py-1.5">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProviderSettings({ onClose }) {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("providers");
  const [migrating, setMigrating] = useState(false);
  const [migrated, setMigrated] = useState(null);

  const refresh = async () => {
    try {
      const r = await api.get("/providers/");
      setConfigs(r.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  const handleSave = async (payload) => {
    await api.post("/providers/save", payload);
    await refresh();
  };

  const handleDelete = async (provider) => {
    await api.delete(`/providers/${provider}`);
    await refresh();
  };

  const handleTest = async (provider) => {
    try {
      const r = await api.post(`/providers/test/${provider}`);
      await refresh();
      return r.data;
    } catch (e) {
      return { connected: false, error: e.response?.data?.detail || "Failed" };
    }
  };

  const handleMigrateEnv = async () => {
    setMigrating(true);
    try {
      const r = await api.post("/providers/setup/migrate-env", { confirm: true });
      setMigrated(r.data);
      await refresh();
    } catch (e) { console.error(e); }
    finally { setMigrating(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-2xl max-h-[90vh] bg-panel border border-line rounded-md shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-line shrink-0">
          <div>
            <h2 className="text-[14px] font-semibold">Provider Settings</h2>
            <p className="text-[11px] text-muted font-mono">Manage 9 providers · No code editing required</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-text transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-5 pt-3 shrink-0">
          {["providers", "routing", "migration"].map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`text-[12px] font-medium px-3 py-1.5 rounded-md transition-colors capitalize ${
                activeTab === tab ? "bg-line text-text" : "text-muted hover:text-text"
              }`}>
              {tab === "routing" ? "Auto-Routing" : tab === "migration" ? ".env Migration" : "Providers"}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {activeTab === "providers" && (
            loading ? (
              <div className="flex items-center gap-2 text-[12px] text-muted py-4">
                <Loader2 size={13} className="animate-spin" /> Loading providers...
              </div>
            ) : (
              <div className="space-y-2">
                {configs.map(config => (
                  <ProviderCard
                    key={config.provider}
                    config={config}
                    onSave={handleSave}
                    onDelete={handleDelete}
                    onTest={handleTest}
                  />
                ))}
              </div>
            )
          )}

          {activeTab === "routing" && <RoutingRulesSection />}

          {activeTab === "migration" && (
            <div>
              <h3 className="text-[13px] font-semibold mb-1">.env Key Migration</h3>
              <p className="text-[12px] text-muted leading-relaxed mb-4">
                If you have API keys currently in your <code className="font-mono text-signal">.env</code> file,
                this will import them once into encrypted database storage.
                After migration, you can remove them from .env — the app will never need .env for provider keys again.
              </p>
              {migrated ? (
                <div className="bg-signal/5 border border-signal/20 rounded-md p-4">
                  <p className="text-[12px] text-signal font-mono">{migrated.message}</p>
                  {migrated.migrated?.length > 0 && (
                    <p className="text-[11px] text-muted mt-1">Migrated: {migrated.migrated.join(", ")}</p>
                  )}
                </div>
              ) : (
                <button
                  onClick={handleMigrateEnv}
                  disabled={migrating}
                  className="flex items-center gap-2 bg-signal/10 border border-signal/40 text-signal text-[13px] font-medium px-4 py-2 rounded-md hover:bg-signal/20 transition-colors disabled:opacity-50"
                >
                  {migrating ? <Loader2 size={14} className="animate-spin" /> : <Shield size={14} />}
                  {migrating ? "Migrating..." : "Import .env Keys to Secure Storage"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
