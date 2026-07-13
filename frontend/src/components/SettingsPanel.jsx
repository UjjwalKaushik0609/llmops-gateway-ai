import React, { useEffect, useState } from "react";
import { Key, Plus, Trash2, X, ShieldCheck, Loader2 } from "lucide-react";
import { listApiKeys, addApiKey, deleteApiKey } from "../lib/api";

const PROVIDERS = [
  { id: "gemini", label: "Gemini", color: "#3DD68C" },
  { id: "openai", label: "OpenAI", color: "#5B8DEF" },
  { id: "anthropic", label: "Anthropic", color: "#9B7BF5" },
  { id: "mistral", label: "Mistral", color: "#F0A742" },
];

export default function SettingsPanel({ onClose }) {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [provider, setProvider] = useState("gemini");
  const [keyName, setKeyName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const res = await listApiKeys();
      setKeys(res.data || []);
    } catch (err) {
      console.error("Failed to load keys", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await addApiKey(provider, keyName || `${provider} key`, apiKey);
      setKeyName("");
      setApiKey("");
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save key");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteApiKey(id);
      await refresh();
    } catch (err) {
      console.error("Failed to delete key", err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-lg bg-panel border border-line rounded-md shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <div className="flex items-center gap-2">
            <Key size={15} className="text-signal" />
            <h2 className="text-[14px] font-semibold">Your API Keys</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-text transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4">
          <div className="bg-signal/5 border border-signal/20 rounded-md px-3 py-2.5 mb-5 flex gap-2">
            <ShieldCheck size={14} className="text-signal shrink-0 mt-0.5" />
            <p className="text-[11.5px] text-muted leading-relaxed">
              Keys are encrypted before storage and used only for your own requests.
              If you don't add a key, your requests use the server's shared key
              (may be rate-limited across all users).
            </p>
          </div>

          {/* Existing keys */}
          <div className="mb-5">
            <h3 className="text-[11px] font-mono uppercase tracking-wide text-muted mb-2">
              Saved keys
            </h3>
            {loading ? (
              <div className="flex items-center gap-2 text-[12px] text-muted py-3">
                <Loader2 size={13} className="animate-spin" /> loading...
              </div>
            ) : keys.length === 0 ? (
              <p className="text-[12px] text-muted font-mono py-2">
                No personal keys saved yet — using server default.
              </p>
            ) : (
              <div className="space-y-2">
                {keys.map((k) => {
                  const meta = PROVIDERS.find((p) => p.id === k.provider) || {};
                  return (
                    <div
                      key={k.id}
                      className="flex items-center justify-between bg-panel2 border border-line rounded-md px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-sm"
                          style={{ color: meta.color, backgroundColor: `${meta.color}1A` }}
                        >
                          {k.provider}
                        </span>
                        <span className="text-[12px] text-text">{k.key_name}</span>
                      </div>
                      <button
                        onClick={() => handleDelete(k.id)}
                        className="text-muted hover:text-red transition-colors"
                        title="Remove key"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Add new key */}
          <form onSubmit={handleAdd} className="space-y-2.5">
            <h3 className="text-[11px] font-mono uppercase tracking-wide text-muted mb-1">
              Add a key
            </h3>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-md px-3 py-2 text-[13px] text-text focus:outline-none focus:border-signal/50"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Label (optional, e.g. 'my personal key')"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-md px-3 py-2 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-signal/50"
            />
            <input
              type="password"
              placeholder="Paste your API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              minLength={10}
              className="w-full bg-panel2 border border-line rounded-md px-3 py-2 text-[13px] text-text placeholder:text-muted focus:outline-none focus:border-signal/50 font-mono"
            />

            {error && <p className="text-[12px] text-red font-mono">{error}</p>}

            <button
              type="submit"
              disabled={submitting || !apiKey}
              className="w-full bg-signal/10 border border-signal/40 text-signal text-[13px] font-medium py-2 rounded-md hover:bg-signal/20 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {submitting ? "Saving..." : "Save key"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
