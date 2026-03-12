'use client'
import { useEffect, useState } from 'react'
import { Settings, Save, Eye, EyeOff, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'

const FIELDS = [
  {
    key: 'OPENROUTER_API_KEY',
    label: 'OpenRouter API Key',
    secret: true,
    placeholder: 'sk-or-...',
    desc: 'Required for all agents. Get from openrouter.ai/keys',
    link: 'https://openrouter.ai/keys'
  },
  {
    key: 'SERPER_API_KEY',
    label: 'Serper.dev API Key',
    secret: true,
    placeholder: 'Your Serper key',
    desc: 'For SERP analysis. Get from serper.dev',
    link: 'https://serper.dev'
  },
  {
    key: 'DATAFORSEO_LOGIN',
    label: 'DataForSEO Login',
    secret: false,
    placeholder: 'your@email.com',
    desc: 'For keyword volume + difficulty data'
  },
  {
    key: 'DATAFORSEO_PASSWORD',
    label: 'DataForSEO Password',
    secret: true,
    placeholder: '••••••••',
    desc: 'DataForSEO account password'
  },
  {
    key: 'GSC_CREDENTIALS_PATH',
    label: 'Google Search Console Credentials Path',
    secret: false,
    placeholder: '/path/to/gsc-credentials.json',
    desc: 'Absolute path to your GSC service account JSON file'
  },
  {
    key: 'GA4_CREDENTIALS_PATH',
    label: 'GA4 Credentials Path',
    secret: false,
    placeholder: '/path/to/ga4-credentials.json',
    desc: 'Absolute path to your GA4 service account JSON file'
  },
  {
    key: 'GA4_PROPERTY_ID',
    label: 'GA4 Property ID',
    secret: false,
    placeholder: 'properties/123456789',
    desc: 'Your GA4 property ID (found in GA4 Admin → Property Settings)'
  },
]

// Grouped by provider for the per-agent model selector
const MODEL_GROUPS = [
  {
    label: 'Anthropic',
    models: [
      { value: 'anthropic/claude-sonnet-4-5',      label: 'Claude Sonnet 4.5' },
      { value: 'anthropic/claude-haiku-4-5',        label: 'Claude Haiku 4.5 (fast + cheap)' },
      { value: 'anthropic/claude-opus-4-5',         label: 'Claude Opus 4.5 (most capable)' },
    ]
  },
  {
    label: 'OpenAI',
    models: [
      { value: 'openai/gpt-4o',                    label: 'GPT-4o' },
      { value: 'openai/gpt-4o-mini',               label: 'GPT-4o Mini (cheap)' },
    ]
  },
  {
    label: 'Google',
    models: [
      { value: 'google/gemini-flash-2.0',          label: 'Gemini Flash 2.0 (fast)' },
      { value: 'google/gemini-pro-1.5',            label: 'Gemini Pro 1.5' },
    ]
  },
  {
    label: 'Meta / Open Source',
    models: [
      { value: 'meta-llama/llama-3.3-70b-instruct', label: 'Llama 3.3 70B' },
      { value: 'deepseek/deepseek-chat',            label: 'DeepSeek V3 (very cheap)' },
    ]
  },
]

const ALL_MODELS = MODEL_GROUPS.flatMap(g => g.models)

const AGENT_MODEL_KEYS = [
  { key: 'research_model',  label: 'Research Agent',  desc: 'Keyword research + SERP analysis' },
  { key: 'content_model',   label: 'Content Agent',   desc: 'Outline + full article writing (use best model)' },
  { key: 'onpage_model',    label: 'On-Page Agent',   desc: 'Scoring + optimization' },
  { key: 'links_model',     label: 'Links Agent',     desc: 'Cluster + internal linking' },
  { key: 'memory_model',    label: 'Memory Agent',    desc: 'Learning extraction' },
]

function ModelSelect({ value, onChange }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent transition-colors">
      {MODEL_GROUPS.map(group => (
        <optgroup key={group.label} label={group.label}>
          {group.models.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}

export default function SettingsPage() {
  const [config, setConfig] = useState({})
  const [modelSettings, setModelSettings] = useState({
    model: 'anthropic/claude-sonnet-4-5',
    research_model: 'openai/gpt-4o-mini',
    content_model: 'anthropic/claude-sonnet-4-5',
    onpage_model: 'openai/gpt-4o-mini',
    links_model: 'openai/gpt-4o-mini',
    memory_model: 'openai/gpt-4o-mini',
    max_tokens: 4096,
    temperature: 0.3
  })
  const [pipelineSettings, setPipelineSettings] = useState({
    max_retries: 3,
    retry_delay: 5,
    timeout_per_stage: 120
  })
  const [visible, setVisible] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/config')
      .then(r => r.json())
      .then(d => {
        setConfig(d.env || {})
        if (d.model) setModelSettings(prev => ({ ...prev, ...d.model }))
        if (d.pipeline) setPipelineSettings(d.pipeline)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ env: config, model: modelSettings, pipeline: pipelineSettings })
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="animate-fade-in max-w-3xl">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted uppercase tracking-widest mb-2">
            <Settings size={10} /> Configuration
          </div>
          <h1 className="font-sans text-3xl font-bold text-white tracking-tight">Settings</h1>
          <p className="text-muted text-xs mt-1">API keys · Model selection · Pipeline config</p>
        </div>
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent text-bg text-xs font-bold rounded hover:bg-accent/90 transition-colors disabled:opacity-50">
          {saving
            ? <span className="w-3 h-3 border border-bg border-t-transparent rounded-full animate-spin" />
            : <Save size={12} />
          }
          {saved ? 'SAVED ✓' : 'SAVE CONFIG'}
        </button>
      </div>

      {saved && (
        <div className="mb-4 bg-accent3/10 border border-accent3/30 rounded px-4 py-3 text-xs text-accent3 flex items-center gap-2">
          <CheckCircle size={12} /> Configuration saved — restart dev server for API key changes to take effect
        </div>
      )}

      {/* API Keys */}
      <div className="bg-surface border border-border rounded overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border bg-surface2">
          <div className="text-xs font-bold text-white tracking-wide">API KEYS</div>
          <div className="text-xs text-muted mt-0.5">Stored in .env.local — never sent to the browser</div>
        </div>
        <div className="p-5 space-y-5">
          {FIELDS.map(field => (
            <div key={field.key}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-white flex items-center gap-2">
                  {field.label}
                  {field.link && (
                    <a href={field.link} target="_blank" rel="noreferrer"
                      className="text-muted hover:text-accent transition-colors">
                      <ExternalLink size={10} />
                    </a>
                  )}
                </label>
                <span className={`text-xs px-2 py-0.5 rounded border ${
                  config[field.key]
                    ? 'text-accent3 bg-accent3/10 border-accent3/20'
                    : 'text-muted bg-dim/20 border-dim/20'
                }`}>
                  {config[field.key] ? '● Connected' : '○ Not set'}
                </span>
              </div>
              <div className="relative">
                <input
                  type={field.secret && !visible[field.key] ? 'password' : 'text'}
                  value={config[field.key] || ''}
                  onChange={e => setConfig(c => ({ ...c, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                  className="w-full bg-surface2 border border-border rounded px-4 py-2.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent transition-colors pr-10"
                />
                {field.secret && (
                  <button type="button"
                    onClick={() => setVisible(v => ({ ...v, [field.key]: !v[field.key] }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white transition-colors">
                    {visible[field.key] ? <EyeOff size={12} /> : <Eye size={12} />}
                  </button>
                )}
              </div>
              <div className="text-xs text-muted mt-1">{field.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Default Model */}
      <div className="bg-surface border border-border rounded overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border bg-surface2">
          <div className="text-xs font-bold text-white tracking-wide">DEFAULT MODEL</div>
          <div className="text-xs text-muted mt-0.5">Used when no per-agent override is set</div>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs text-white mb-1.5">Fallback Model</label>
            <ModelSelect
              value={modelSettings.model}
              onChange={v => setModelSettings(m => ({ ...m, model: v }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-white mb-1.5">
                Max Tokens <span className="text-muted">({modelSettings.max_tokens})</span>
              </label>
              <input type="range" min="1000" max="8192" step="256"
                value={modelSettings.max_tokens}
                onChange={e => setModelSettings(m => ({ ...m, max_tokens: parseInt(e.target.value) }))}
                className="w-full accent-cyan-400" />
            </div>
            <div>
              <label className="block text-xs text-white mb-1.5">
                Temperature <span className="text-muted">({modelSettings.temperature})</span>
              </label>
              <input type="range" min="0" max="1" step="0.1"
                value={modelSettings.temperature}
                onChange={e => setModelSettings(m => ({ ...m, temperature: parseFloat(e.target.value) }))}
                className="w-full accent-cyan-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Per-Agent Models */}
      <div className="bg-surface border border-border rounded overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border bg-surface2">
          <div className="text-xs font-bold text-white tracking-wide">PER-AGENT MODEL OVERRIDES</div>
          <div className="text-xs text-muted mt-0.5">Use cheap models for analysis, best model for writing</div>
        </div>
        <div className="p-5 space-y-4">
          {AGENT_MODEL_KEYS.map(agent => (
            <div key={agent.key}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-white">{agent.label}</label>
                <span className="text-xs text-muted">{agent.desc}</span>
              </div>
              <ModelSelect
                value={modelSettings[agent.key] || modelSettings.model}
                onChange={v => setModelSettings(m => ({ ...m, [agent.key]: v }))}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Settings */}
      <div className="bg-surface border border-border rounded overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border bg-surface2 text-xs font-bold text-white tracking-wide">
          PIPELINE SETTINGS
        </div>
        <div className="p-5 grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-white mb-1.5">Max Retries</label>
            <input type="number" min="1" max="10" value={pipelineSettings.max_retries}
              onChange={e => setPipelineSettings(p => ({ ...p, max_retries: parseInt(e.target.value) }))}
              className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent transition-colors" />
          </div>
          <div>
            <label className="block text-xs text-white mb-1.5">Retry Delay (sec)</label>
            <input type="number" min="1" max="60" value={pipelineSettings.retry_delay}
              onChange={e => setPipelineSettings(p => ({ ...p, retry_delay: parseInt(e.target.value) }))}
              className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent transition-colors" />
          </div>
          <div>
            <label className="block text-xs text-white mb-1.5">Stage Timeout (sec)</label>
            <input type="number" min="30" max="600" value={pipelineSettings.timeout_per_stage}
              onChange={e => setPipelineSettings(p => ({ ...p, timeout_per_stage: parseInt(e.target.value) }))}
              className="w-full bg-surface2 border border-border rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-accent transition-colors" />
          </div>
        </div>
      </div>

      <div className="bg-accent4/5 border border-accent4/20 rounded p-4">
        <div className="flex items-start gap-2 text-xs">
          <AlertCircle size={12} className="text-accent4 mt-0.5 flex-shrink-0" />
          <div className="text-muted leading-relaxed">
            API keys are written to <span className="text-white">.env.local</span>. Model and pipeline settings go to <span className="text-white">config.json</span>. Restart the dev server after saving API key changes. Per-agent model overrides take effect immediately on next run.
          </div>
        </div>
      </div>
    </div>
  )
}
